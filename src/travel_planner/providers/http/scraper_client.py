"""The shared ScraperClient - every responsible-scraping rule lives here.

No individual scraper may fetch a URL directly; all fetching goes through this
client so the rules cannot be forgotten in a new provider (ADR-006):

* **SSRF-safe** - only http/https, private/loopback IPs and unusual ports rejected.
* **robots.txt** - checked and honoured per domain (cacheable, disabled for tests).
* **Identifiable User-Agent** with a contact URL, never a spoofed browser.
* **Per-domain rate limiting** - default <=1 request per 2 seconds, with jitter.
* **Exponential backoff** - honours ``Retry-After`` on 429/503.
* **Timeouts** on every request.
* **Per-source circuit breaker** - repeated failures open the circuit and the
  registry falls down the chain instead of hammering a dead site.
* **In-memory cache with TTL** - prices expire in hours, place info in days.
* **Sanitization** - scripts, styles and event handlers are stripped before any
  caller (or any LLM) sees the content.

Logins, paywalls, CAPTCHAs and IP blocks are never bypassed; there is no proxy
rotation and no fingerprint spoofing by design.
"""

from __future__ import annotations

import ipaddress
import logging
import random
import re
import socket
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass

import httpx

from travel_planner.errors import ProviderUnavailableError, ScrapingNotPermittedError

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_ALLOWED_PORTS = frozenset({80, 443, None})

_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.IGNORECASE | re.DOTALL)
_HANDLER_RE = re.compile(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)
_IFRAME_RE = re.compile(r"<iframe\b[^>]*>.*?</iframe\s*>", re.IGNORECASE | re.DOTALL)

#: JSON-LD blocks are structured data, not executable code - they must survive
#: sanitization so the scrapers can parse them.
_JSONLD_SCRIPT_RE = re.compile(
    r"(<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>.*?</script\s*>)",
    re.IGNORECASE | re.DOTALL,
)

_INJECTION_MARKERS = (
    "ignore previous instructions",
    "disregard the above",
    "system prompt",
    "you are now",
    "jailbreak",
)


def sanitize_html(html: str) -> str:
    """Strip scripts, styles, iframes and inline handlers from untrusted HTML.

    ``application/ld+json`` script blocks are preserved: they are structured
    data, not executable code, and the scrapers depend on them.
    """
    # 1. Park the JSON-LD blocks aside.
    ld_blocks: list[str] = []
    def _park(match: re.Match[str]) -> str:
        ld_blocks.append(match.group(1))
        return f"__JSONLD_{len(ld_blocks) - 1}__"

    staged = _JSONLD_SCRIPT_RE.sub(_park, html)

    # 2. Strip everything dangerous.
    cleaned = _SCRIPT_RE.sub(" ", staged)
    cleaned = _STYLE_RE.sub(" ", cleaned)
    cleaned = _IFRAME_RE.sub(" ", cleaned)
    cleaned = _HANDLER_RE.sub(" ", cleaned)

    # 3. Restore the JSON-LD blocks.
    for index, block in enumerate(ld_blocks):
        cleaned = cleaned.replace(f"__JSONLD_{index}__", block)
    return cleaned


def sanitize_for_llm(text: str) -> str:
    """Best-effort prompt-injection screen for text about to reach a model.

    Markers are removed, not just flagged - page content must never drive tool
    execution. This is defence in depth, not a guarantee.
    """
    lowered = text.lower()
    if not any(marker in lowered for marker in _INJECTION_MARKERS):
        return text
    cleaned = text
    for marker in _INJECTION_MARKERS:
        cleaned = re.sub(re.escape(marker), "[removed]", cleaned, flags=re.IGNORECASE)
    logger.warning("stripped prompt-injection marker(s) from untrusted content")
    return cleaned


def is_private_host(host: str) -> bool:
    """True for loopback, private, link-local or reserved addresses."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # An unresolvable host is not an SSRF risk; the request itself will fail.
        return False
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def validate_public_http_url(url: str) -> urllib.parse.ParseResult:
    """Reject anything that is not a plain public http(s) URL (SSRF defence)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        msg = f"Rejected URL scheme {parsed.scheme!r} (SSRF guard)"
        raise ScrapingNotPermittedError(msg)
    if parsed.port not in _ALLOWED_PORTS:
        msg = f"Rejected non-standard port {parsed.port!r} (SSRF guard)"
        raise ScrapingNotPermittedError(msg)
    if not parsed.hostname:
        msg = "Rejected URL without a hostname (SSRF guard)"
        raise ScrapingNotPermittedError(msg)
    if is_private_host(parsed.hostname):
        msg = f"Rejected private/reserved host {parsed.hostname!r} (SSRF guard)"
        raise ScrapingNotPermittedError(msg)
    return parsed


@dataclass
class CachedResponse:
    """A cached page with its retrieval time, for TTL checks."""

    body: str
    fetched_at: float
    etag: str | None = None
    last_modified: str | None = None


class ScraperClient:
    """The only approved way to fetch a web page in this codebase."""

    def __init__(
        self,
        *,
        user_agent: str,
        rate_limit_per_second: float = 0.5,
        respect_robots: bool = True,
        timeout: float = 20.0,
        max_retries: int = 3,
        breaker_threshold: int = 3,
        breaker_cooldown: float = 300.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._min_interval = 1.0 / rate_limit_per_second if rate_limit_per_second > 0 else 2.0
        self._respect_robots = respect_robots
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = client or httpx.Client(
            headers={"User-Agent": user_agent}, follow_redirects=True, timeout=timeout
        )
        self._last_request_at: dict[str, float] = {}
        self._cache: dict[str, CachedResponse] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._breaker_counts: dict[str, int] = {}
        self._breaker_opened_at: dict[str, float] = {}
        self._breaker_threshold = breaker_threshold
        self._breaker_cooldown = breaker_cooldown
        self._injected_robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    # ------------------------------------------------------------- circuit
    def _breaker_open(self, key: str) -> bool:
        opened = self._breaker_opened_at.get(key)
        if opened is None:
            return False
        if time.monotonic() - opened >= self._breaker_cooldown:
            # Half-open: allow a single probe.
            self._breaker_opened_at.pop(key, None)
            self._breaker_counts[key] = self._breaker_threshold - 1
            return False
        return True

    def force_failure_for_tests(self, key: str) -> None:
        """Test hook: drive a source's breaker open deterministically."""
        self._breaker_counts[key] = self._breaker_threshold
        self._breaker_opened_at[key] = time.monotonic()

    def _record_success(self, key: str) -> None:
        self._breaker_counts.pop(key, None)
        self._breaker_opened_at.pop(key, None)

    def _record_failure(self, key: str) -> None:
        count = self._breaker_counts.get(key, 0) + 1
        self._breaker_counts[key] = count
        if count >= self._breaker_threshold:
            self._breaker_opened_at[key] = time.monotonic()
            logger.warning("circuit opened for %s after %d failures", key, count)

    # --------------------------------------------------------------- robots
    def inject_robots_for_tests(
        self, host: str, parser: urllib.robotparser.RobotFileParser
    ) -> None:
        """Test hook: pretend robots.txt said this, without any network."""
        self._injected_robots[host] = parser

    def _robots_allows(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        if host in self._injected_robots:
            return self._injected_robots[host].can_fetch(self._user_agent, url)
        if not self._respect_robots:
            return True
        if host not in self._robots:
            self._robots[host] = self._load_robots(parsed.scheme, host)
        parser = self._robots[host]
        if parser is None:
            # robots.txt could not be fetched; allow the fetch (conservative).
            return True
        return parser.can_fetch(self._user_agent, url)

    def _load_robots(self, scheme: str, host: str) -> urllib.robotparser.RobotFileParser | None:
        robots_url = f"{scheme}://{host}/robots.txt"
        try:
            response = self._client.get(robots_url, timeout=self._timeout)
        except httpx.HTTPError as exc:
            logger.info("robots.txt fetch failed for %s: %s", host, exc)
            return None
        if response.status_code >= 400:
            logger.info("no robots.txt at %s (status %d)", host, response.status_code)
            return None
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser

    # ---------------------------------------------------------- rate limit
    def _respect_rate_limit(self, host: str) -> None:
        """Block until the per-domain interval has elapsed, with jitter."""
        last = self._last_request_at.get(host, 0.0)
        elapsed = time.monotonic() - last
        wait = self._min_interval - elapsed
        if wait > 0:
            jitter = random.uniform(0, 0.25) * self._min_interval
            time.sleep(wait + jitter)
        self._last_request_at[host] = time.monotonic()

    # ----------------------------------------------------------------- fetch
    def fetch(
        self,
        url: str,
        *,
        ttl_seconds: float | None = None,
        use_cache: bool = True,
    ) -> str:
        """Fetch a public page and return sanitized HTML.

        Raises :class:`ScrapingNotPermittedError` for SSRF/robots violations and
        :class:`ProviderUnavailableError` for network failures - never a raw
        ``httpx`` exception, so every scraper behaves the same.
        """
        parsed = validate_public_http_url(url)
        host = parsed.hostname or ""

        cached = self._cache.get(url)
        if (
            use_cache
            and cached is not None
            and (ttl_seconds is None or time.monotonic() - cached.fetched_at < ttl_seconds)
        ):
            logger.debug("cache hit for %s", url)
            return cached.body

        if self._breaker_open(host):
            msg = f"circuit open for {host}; falling back"
            raise ProviderUnavailableError(msg)

        if not self._robots_allows(url):
            msg = f"robots.txt disallows {url}"
            raise ScrapingNotPermittedError(msg)

        headers: dict[str, str] = {}
        if cached is not None:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.last_modified:
                headers["If-Modified-Since"] = cached.last_modified

        delay = 1.0
        last_error = "unknown"
        for _ in range(self._max_retries + 1):
            self._respect_rate_limit(host)
            try:
                response = self._client.get(url, headers=headers, timeout=self._timeout)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.info("fetch failed for %s: %s", url, exc)
                time.sleep(delay)
                delay *= 2
                continue

            if response.status_code == 304 and cached is not None:
                cached.fetched_at = time.monotonic()
                self._record_success(host)
                return cached.body

            if response.status_code in (429, 503):
                retry_after = response.headers.get("Retry-After")
                wait_for = float(retry_after) if retry_after and retry_after.isdigit() else delay
                logger.info("rate limited on %s; backing off %.1fs", url, wait_for)
                last_error = f"HTTP {response.status_code}"
                time.sleep(wait_for)
                delay *= 2
                continue

            if response.status_code >= 400:
                self._record_failure(host)
                msg = f"HTTP {response.status_code} for {url}"
                raise ProviderUnavailableError(msg)

            body = sanitize_html(response.text)
            self._cache[url] = CachedResponse(
                body=body,
                fetched_at=time.monotonic(),
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
            self._record_success(host)
            return body

        self._record_failure(host)
        msg = f"fetch failed for {url} after retries: {last_error}"
        raise ProviderUnavailableError(msg)

    def cache_size(self) -> int:
        """Number of cached responses (for observability and tests)."""
        return len(self._cache)

    def clear_cache(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self._client.close()


def build_scraper_client_from_settings(
    client: httpx.Client | None = None,
) -> ScraperClient:
    """Build the shared client from env settings."""
    from travel_planner.config.settings import get_settings

    settings = get_settings()
    return ScraperClient(
        user_agent=settings.scraper_user_agent,
        rate_limit_per_second=settings.scraper_rate_limit_per_second,
        respect_robots=settings.scraper_respect_robots,
        timeout=settings.scraper_timeout,
        client=client,
    )


