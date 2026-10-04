# Agentic Travel Planner

An AI product that plans and manages an **entire trip** - for **domestic Iran trips and
international trips**, in **Persian (RTL) and English** - built on a deterministic,
source-grounded core.

**Status: all 10 phases complete.** See [FINAL-REPORT.md](FINAL-REPORT.md) for the honest
summary (what is verified, what is implemented-but-unverified, and the known limitations),
or the per-phase gates in `STATUS-P0.md` ... `STATUS-P9.md`.

## Features

**Before the trip** - natural-language request -> a typed `TripRequest`; a day-by-day
itinerary with optimized routes, per-day and total budgets in labelled Toman; a packing
list and document checklist; advisory entry requirements for international travel (always
with the "verify with official source" warning); seasonal planning.

**During the trip (Live Mode)** - today's plan with next-stop hints; a one-tap re-plan for
rain, a closed venue, running late, tiredness or a budget change (the reason is recorded on
the agent trace); an expense tracker with currency conversion and a budget burn-down; an
offline-capable PWA (service worker caching).

**After the trip** - the full plan history (itinerary versions are append-only), a public
read-only share link, ICS and PDF exports.

## The four differentiators (all genuinely implemented)

| Differentiator | How it works |
|---|---|
| Source-grounded facts | Every external fact carries `confirmed / estimated / inferred / unavailable` plus a source and a retrieval time. Unavailable data is labelled unavailable - it is never invented. |
| Deterministic optimization | Routes, times, workload caps and budgets are computed by Python (clustering, nearest-neighbour + 2-opt, the 8h cap). The LLM never guesses a plan. |
| Conversational edits | One-tap re-plan reasons are typed, validated and traced; each run is a new version, history is never overwritten. |
| Transparent agent trace | Structured steps with timings. The chain-of-thought is stripped at the model-client boundary and never stored or shown. |

## Architecture (short version)

- **LangGraph** workflow over a typed, checkpointed `TravelState` - 9 parallel research
  nodes -> a deterministic planner/validator -> a bounded replan loop -> a Persian/English
  writer. Full detail: [docs/agents.md](docs/agents.md).
- **Provider-agnostic LLM layer**: `apmix | openai | openai_compatible | ollama | mock`.
  In `mock` the whole product runs offline with zero keys.
- **Scraping-first, API-ready providers**: every capability is a `Protocol` with an
  env-driven fallback chain ([docs/data-sources.md](docs/data-sources.md)); the shared
  `ScraperClient` enforces SSRF guards, robots.txt, rate limits, circuit breakers,
  caching and sanitization in one place.
- **FastAPI + SQLAlchemy** (SQLite for zero-setup, Postgres in production), one error
  envelope, request IDs, Prometheus metrics at `/api/v1/metrics`.
- **Next.js 16** web app with fa/en, full RTL, Persian digits and a service worker.
- Full docs: [docs/architecture.md](docs/architecture.md),
  [docs/api.md](docs/api.md), [docs/deployment.md](docs/deployment.md),
  [docs/security.md](docs/security.md), [docs/monetization.md](docs/monetization.md),
  [docs/iran-mode.md](docs/iran-mode.md), [docs/evaluation.md](docs/evaluation.md),
  [docs/tools.md](docs/tools.md).

## Quick start (offline demo - no keys needed)

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -e ".[dev,api]"
copy .env.example .env                            # set JWT_SECRET at minimum
set LLM_PROVIDER=mock

uvicorn travel_planner.api.app:app --port 8000    # API  -> http://localhost:8000

cd web && npm ci && npm run build && npm start     # web  -> http://localhost:3000
```

Or plan from the CLI:

```bash
travel-planner plan --demo --nights 3 --start 2026-11-01   # offline Tehran -> Shiraz
```

## Docker (full stack)

```bash
export JWT_SECRET=<a long random string>
docker compose up --build        # api :8000, web :3000, postgres, redis
```

Boots in offline demo mode by default. See [docs/deployment.md](docs/deployment.md)
for leaving demo mode and the production checklist.

## Testing and evaluation

```bash
ruff check src tests scripts     # lint
mypy                             # strict types
pytest -q -m "not live"          # 211 offline tests
pytest -m live                   # 12 opt-in tests against real providers
npx playwright test              # the golden path (boots the stack itself, from web/)
python evaluation/runner.py      # the evaluation gate: 25 scenarios
```

Real numbers: **211 offline tests, 25/25 evaluation scenarios (100%), mean scenario
latency 70.5 ms offline**, and a 12-test live suite covering the apmix gateway,
Open-Meteo and OSRM. The committed evaluation report lives in
`evaluation/reports/`.

## Environment variables

All configuration is env-driven (see `.env.example`). The essentials:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `mock` (offline), `apmix`, `openai`, `openai_compatible`, `ollama` |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | the gateway credentials (never committed) |
| `DATABASE_URL` | SQLite by default; `postgresql+asyncpg://...` in production |
| `JWT_SECRET` | **must** be set to a long random string outside local dev |
| `ADMIN_BOOTSTRAP_EMAIL` | grants the admin role to the first matching account |
| `<CAPABILITY>_PROVIDERS` | the per-capability fallback chains |
| `GUEST_TRIAL_ENABLED` | the 1-free-plan guest trial on/off |

## Roadmap

- Richer provider-backed venues (indoor/outdoor attributes) so re-plan reasons
  can swap venues instead of re-running the whole plan.
- OAuth (Google), referral credits and OG share images.
- The web checklist/expense screens on top of the finished API.
- Redis-backed distributed rate limiting and caching.
- A real OTLP collector for the already-emitted spans.

## License

To be decided. All rights reserved until a license is chosen.

## Legal note

Visa and entry-requirement information is advisory only and must be verified with an
official source before travel. Scraping follows each site's robots.txt and is recorded in
`docs/data-sources.md`; enabling a scraper against a real site requires the owner's
review of that site's terms. Privacy and ToS templates need legal review.
