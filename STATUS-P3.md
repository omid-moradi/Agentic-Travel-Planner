# STATUS - Phase 3 (Data providers, scraping-first)

Date: 2026-10-03
Branch: `phase/3-providers`
Gate: parser contract tests green + documented live smoke tests. **Passed.**

---

## Done

- [x] `travel_planner.providers.base` - the provider abstraction:
      seven capability `Protocol`s, `ProviderResult` with provenance,
      `ProviderRegistry` with ordered fallback chains, `CircuitBreaker`
      (open, half-open, reset).
- [x] `travel_planner.providers.http.scraper_client` - the shared ScraperClient
      enforcing every responsible-scraping rule in one place:
      SSRF guard (scheme/port/private-IP/cloud-metadata), robots.txt honoured,
      identifiable User-Agent, per-domain rate limit with jitter, exponential
      backoff honouring `Retry-After`, per-source circuit breaker, TTL cache with
      conditional requests (ETag / If-Modified-Since), HTML sanitization that
      preserves `application/ld+json` data blocks, prompt-injection screening.
- [x] `travel_planner.providers.http.jsonld` - the JSON-LD / schema.org parser:
      `@graph` expansion, malformed blocks skipped not fatal, records without a
      name rejected (parser contract).
- [x] `travel_planner.providers.places.scraper_jsonld` - the reference scraper:
      fetches only through the ScraperClient, parses JSON-LD first, rejects
      records without coordinates. Pointed at **no real third-party site** until
      robots.txt + ToS review is recorded (see docs/data-sources.md).
- [x] Curated providers: `curated_places`, `curated_hotels`, `curated_transport`
      (refuses unknown city pairs instead of inventing prices).
- [x] `estimator_ride_fare` - calibrated formula
      `base + per_km * distance + per_minute * minutes x time-of-day`,
      Tehran/Shiraz/Isfahan calibrated, always labelled **estimated**;
      private app endpoints (Snapp/Tapsi) deliberately never probed.
- [x] Live API providers (free, keyless): `open_meteo` weather (refuses dates
      beyond the forecast window - honest unavailable), `osrm` routing
      (self-hostable via `OSRM_BASE_URL`).
- [x] `registry_factory` - chains resolved from env per capability;
      unknown names are logged and skipped, never fatal; scrapers stay
      disabled until explicitly configured; offline mode drops live APIs.
- [x] `docs/data-sources.md` + `SOURCES.md` - every source with method, risk,
      status, the rejected-sources list with reasons, the responsible-scraping
      rules, the add-a-scraper checklist, and open legal questions for the owner.
- [x] Parser contract tests against a **saved HTML fixture**
      (`tests/fixtures/html/attractions_shiraz.html`), including a deliberately
      malformed JSON-LD block and injected scripts that must not survive.
- [x] Live smoke tests for Open-Meteo and OSRM (opt-in, `-m live`).

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 40 files) | **Success: no issues found** |
| Offline tests | `pytest -q -m "not live"` | **149 passed** |
| Coverage | `pytest --cov` | **80% total** |
| **Gate: parser contract tests** | `pytest tests/unit/test_scraper_client.py` | **26 passed** |
| Live provider smoke | `pytest -m live` (providers) | **5 passed** against real Open-Meteo and OSRM |
| Live LLM smoke | `pytest -m live` (gateway) | **7 passed** against apmix |
| Phase 2 gate still green | `travel-planner plan --demo --nights 3` | exit 0, valid offline plan |

Live findings recorded honestly:

- **Open-Meteo returns HTTP 400** for dates beyond its ~16-day window instead of
  clamping; the provider surfaces this as `ProviderUnavailableError` and a live
  test pins that behaviour (honesty over invention, ADR-009).
- **OSRM Tehran->Shiraz** returned a driving distance within the expected
  700-1100 km band - verified live, not assumed.
- **The free-tier LLM drifts** on vague JSON instructions; the live JSON-mode
  test now names the exact keys, and the finding is documented in the test.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| The reference scraper against a real site | deliberately pointed at no real third-party site until robots.txt + ToS review is recorded in docs/data-sources.md | pick a candidate site, run the checklist in docs/data-sources.md, then run the canary |
| Nightly canary job | the scheduler lands with the background jobs of phase 4+; the parser contract it would run is already tested | phase 4 |
| Redis-backed cache and rate limits | Redis is not available in this environment (declared limitation); the in-memory implementation is correct and swappable | phase 4 |
| Nominatim geocoding, currency, restaurants, events providers | interfaces registered in the chains but no concrete providers yet | later phases |

## Known limitations (honest)

- The curated dataset is small (9 venues, 4 hotels, 1 transport pair) and
  hand-checked-in. Admin import with `last_verified_at` arrives with persistence.
- The rate limiter and circuit breaker are per-process, not distributed; fine
  for a single instance, replaced by Redis in phase 4.
- robots.txt caching is per-client-lifetime; a long-running process re-checks
  per domain only once (acceptable for the current 0.5 req/s policy).

## Decisions taken

- **JSON-LD script blocks are preserved by sanitize_html**: they are structured
  data, not executable code. Everything else script-like is stripped. A test
  pins this so nobody "fixes" it back.
- **No real hotel site is scraped yet.** The reference scraper is complete and
  contract-tested, but enabling it against a real site requires the robots.txt +
  ToS review recorded in docs/data-sources.md. The owner must approve specific
  sites - this is a legal decision, not a technical one (ADR-009).
- **The transport estimator refuses unknown city pairs** rather than inventing
  a price; the registry then reports the honest unavailable.

## Next - Phase 4 (Persistence and API)

1. SQLAlchemy async + Alembic with the full schema; SQLite fallback for tests.
2. Redis (cache, rate limits, job state) with in-process fallbacks.
3. FastAPI `/api/v1`: trips CRUD, messages, replan, trace, sources, share,
   export, usage, health - with SSE streaming of progress and agent trace.
4. Wire the provider registry into the graph's research nodes.
5. Durable LangGraph checkpointing (SQLite/Postgres).
6. Gate: API end-to-end tests green.
