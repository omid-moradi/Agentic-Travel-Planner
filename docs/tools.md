# Tools & MCP

## Provider capabilities (phase 3)

Every capability is a `Protocol` with an env-driven fallback chain
(ADR-006). Swapping a scraper for an official API is a configuration change:

```dotenv
HOTELS_PROVIDERS=curated,estimator
TRANSPORT_PROVIDERS=curated,estimator
RIDE_FARE_PROVIDERS=estimator
WEATHER_PROVIDERS=open_meteo
ROUTES_PROVIDERS=osrm
```

| Capability | Active providers | Notes |
|---|---|---|
| places | `curated_places` (+ `scraper_jsonld_attractions` reserved) | the reference scraper is contract-tested against a saved fixture and deliberately pointed at no real site until the robots/ToS review |
| hotels | `curated_hotels` | nightly rates are labelled heuristics by price level |
| transport | `curated_transport`, `estimator_transport` | refuses unknown city pairs rather than inventing a price |
| ride_fare | `estimator_ride_fare` | calibrated formula (base + per-km + per-minute x time-of-day); Snapp/Tapsi private endpoints are never probed |
| weather | `open_meteo` | keyless; dates beyond the forecast window are honestly unavailable |
| routes | `osrm` | self-hostable via `OSRM_BASE_URL` |

See `docs/data-sources.md` for the full source registry, the
responsible-scraping rules (SSRF guard, robots.txt, rate limits, circuit
breakers, sanitization, prompt-injection screening) and the rejected-sources
list with reasons.

## MCP server (phase 8)

`python -m travel_planner.mcp.server` starts a minimal, dependency-free
JSON-RPC 2.0 stdio server speaking the MCP protocol basics:
`initialize`, `tools/list`, `tools/call`. Tools exposed:

- `plan_trip` - runs the real offline graph and returns the summary
  (validity, cities, days, total cost, warnings, the rendered message)
- `get_health` - server + configuration liveness

Tool failures return JSON-RPC errors instead of crashing the server, and the
core app never imports the MCP module (enforced by a test).
