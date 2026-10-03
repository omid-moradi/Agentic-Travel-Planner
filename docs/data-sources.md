# Data Sources Registry

Every external data source used by the product, how it is accessed, its terms and
its risk level. Updated in every phase that touches data (ADR-006, ADR-009).

Legend:

* **Method**: `api` = official public API · `scrape` = responsible scraping ·
  `curated` = checked-in dataset · `estimator` = documented formula
* **Risk**: `low` = official API or own dataset · `medium` = scraping a
  permissive source · `high` = scraping a source whose ToS must be reviewed
* **Status**: `active` · `reserved` (built but disabled) · `planned`

---

## Active sources

| Capability | Provider | Source | Method | Auth | Risk | Status | Notes |
|---|---|---|---|---|---|---|---|
| weather | `open_meteo` | [Open-Meteo](https://open-meteo.com) | api (keyless) | none | low | active | Free for non-commercial use; fair-use limits; forecast window ~16 days, beyond that it refuses (honest unavailable). Live-verified 2026-10-03. |
| routes | `osrm` | [OSRM demo server](https://router.project-osrm.org) | api (keyless) | none | low | active | Public demo server, no SLA; production should self-host (env `OSRM_BASE_URL`). Live-verified 2026-10-03: Tehran→Shiraz driving. |
| places | `curated_places` | this repository (`data/fixtures/iran.py`) | curated | none | low | active | 9 venues, Tehran/Shiraz; `last_verified 2026-10-01`. |
| hotels | `curated_hotels` | this repository | curated | none | low | active | 4 hotels; nightly rates are labelled heuristics by price level. |
| transport | `curated_transport` | this repository | curated | none | low | active | Tehran↔Shiraz only; refuses unknown pairs rather than inventing. |
| ride_fare | `estimator_ride_fare` | this repository | estimator | none | low | active | Calibrated formula (base + per-km + per-minute × time-of-day); Tehran, Shiraz, Isfahan calibrated. Always labelled **estimated**. |

## Reserved / disabled sources

| Capability | Provider | Source | Method | Risk | Status | Notes |
|---|---|---|---|---|---|---|
| places | `scraper_jsonld_attractions` | example deployment (`example-attractions.test`) | scrape | medium | reserved | The reference scraper implementation. Fully built and contract-tested against a saved fixture, but **deliberately pointed at no real third-party site** until a specific site's robots.txt and ToS have been reviewed (see below). Enabled by configuring a base URL. |

## Rejected / not pursued (with reasons)

| Source | Reason |
|---|---|
| Snapp / Tapsi fare endpoints | The master prompt forbids reverse-engineering private app endpoints. Fares come from the calibrated estimator instead, always labelled estimated. |
| Hotel booking sites (generic) | No partnership exists. No site is scraped until its robots.txt **and** ToS are reviewed and recorded here; a site that prohibits automated access is never scraped. |
| Visa/entry-rule sites | Only advisory output, always with a "verify with official source" warning; a sourced provider arrives in phase 7. |

## Responsible-scraping rules (enforced in `providers/http/scraper_client.py`)

1. **SSRF guard** - only public http/https on standard ports; loopback, private,
   link-local and cloud-metadata addresses are rejected before any request.
2. **robots.txt** - fetched per domain, cached, and honoured. A disallow raises
   `ScrapingNotPermittedError` and the registry falls down the chain.
3. **Identifiable User-Agent** with a contact URL - never a spoofed browser.
4. **Per-domain rate limit** - default <=1 request / 2 seconds, with jitter.
5. **Exponential backoff** - honours `Retry-After` on 429/503.
6. **Circuit breaker** - 3 consecutive failures open the circuit for 5 minutes;
   the chain degrades instead of hammering a dead or changed site.
7. **Caching with TTL** - prices expire in hours, place info in days;
   conditional requests (ETag / If-Modified-Since) are sent when cached.
8. **Sanitization** - scripts, styles, iframes and inline handlers are stripped
   **except** `application/ld+json` blocks, which are data, not code.
9. **Prompt-injection screening** - known injection markers are removed from
   untrusted text before it may reach a model.
10. **Never bypass** - no logins, paywalls, CAPTCHAs, IP blocks, proxy rotation
    or fingerprint spoofing, by design.

## How to add a real scraper (checklist)

1. Review the target site's robots.txt and Terms of Service. Record both here.
   If automated access is prohibited, the site is **rejected** - do not scrape it.
2. Add a fixture of a saved page under `tests/fixtures/html/` and write parser
   contract tests against it (`tests/unit/test_scraper_client.py` is the model).
3. Implement the scraper as a `Protocol` provider that fetches **only** through
   the shared `ScraperClient`, parses JSON-LD first, and rejects records without
   the fields the optimizer needs (name, coordinates).
4. Register it in `registry_factory.py` behind a short name, disabled until the
   site review in step 1 is complete.
5. Add the nightly canary (phase 8): re-fetch one sample page per source and
   fail loudly when the parser contract breaks.

## Open questions for the owner (legal review needed)

- Confirm the commercial-use stance of Open-Meteo for a revenue product
  (their terms permit free non-commercial use; commercial use needs a paid key
  or a self-hosted instance - both drop in through the same provider).
- Whether to self-host OSRM (recommended for production: no SLA on the demo
  server and no rate-limit ambiguity).
- Data licensing for any curated Iran dataset that is later imported from
  third-party sources.
