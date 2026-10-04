# Final Report — Agentic Travel Planner

Date: 2026-10-04 · Repository: `github.com/omid-moradi/Agentic-Travel-Planner`
All ten phase gates passed; each phase's honest status lives in `STATUS-P0.md` … `STATUS-P9.md`.

---

## 1. What was implemented

A full-stack, revenue-oriented travel product: natural-language trip requests →
a typed, validated, day-by-day itinerary with deterministic routing and Toman
budgeting → checklists, advisory entry requirements, expense tracking, ICS/PDF
exports, a PWA, share links, accounts with quotas, and a test-mode payment
layer — for domestic Iran and international trips, in Persian (RTL) and English.

Built from the original AutoGen prototype: **AutoGen was fully retired** (ADR-002)
and the orchestration rebuilt on LangGraph over a typed, checkpointed `TravelState`.

## 2. Architecture

- **Modular monolith**: FastAPI `/api/v1` + SQLAlchemy (SQLite zero-setup,
  Postgres in production), Next.js 16 web app, LangGraph workflow, provider
  registry, evaluation harness, minimal MCP server. No microservices, no vector DB.
- **LLM layer**: provider-agnostic (`apmix | openai | openai_compatible | ollama |
  mock`). `reasoning_content` is stripped at the client boundary; the whole
  product runs offline with `LLM_PROVIDER=mock` and zero keys.
- **Data flow**: request → 9 parallel research nodes (provenance on every finding)
  → deterministic planner (clustering, nearest-neighbour + 2-opt, 8h workload cap,
  Toman budgeting) → code validator → bounded replan → Persian/English writer.
- **Persistence**: 15 tables (users, subscriptions, usage_events, trips,
  trip_messages, trip_preferences, places, sources, itineraries, itinerary_days,
  agent_runs, tool_runs, share_links, affiliate_clicks, webhook_events, expenses);
  itinerary versions are append-only.

## 3. Verified by actually running it

| Gate | Result |
|---|---|
| ruff + mypy strict (70 files) | clean, 0 issues |
| Offline test suite | **211 passed** (schemas, optimizer, providers, scraper client, graph e2e, API e2e, monetization, whole-trip, failure injection, MCP) |
| Live provider tests (opt-in) | **12 passed**: apmix gateway (chat, tools, JSON mode, reasoning stripping, dead endpoint), Open-Meteo (incl. the honest refuse-beyond-forecast-window), OSRM Tehran→Shiraz driving |
| Evaluation (the phase 8 gate) | **25/25 scenarios, 100%**, mean 70.5 ms offline; the report with real numbers is committed in `evaluation/reports/` |
| Playwright golden path | **1 passed** in a real browser against the real API: create → re-plan → share |
| MCP stdio round trip | initialize → tools/list → `plan_trip` returned a valid 2-day plan; unknown methods → −32601 |

## 4. Implemented but NOT verified (explicit)

| Item | Why | How to verify |
|---|---|---|
| Docker images + compose build | the Docker daemon was not running in the dev environment | `docker compose up --build` |
| Stripe / Zarinpal live calls | no credentials exist; adapters are disabled stubs by design | provide test-mode keys, run a checkout + webhook round trip |
| Service-worker offline behaviour | Playwright cannot drive airplane mode | open a trip page, go offline in DevTools, reload |
| An OTLP collector receiving the spans | spans are emitted in the OTLP data model via structured logs; no collector ran here | run any OTel collector against the log stream |
| A live-gateway evaluation run | the harness is config-driven but the committed numbers are offline (tokens = 0, honestly reported) | `LLM_PROVIDER=apmix` + `python evaluation/runner.py` |
| Scraper against a real site | deliberately pointed at none until robots.txt + ToS review is recorded in `docs/data-sources.md` | pick a candidate site, run the checklist, get owner approval |

## 5. Known limitations (explicit)

- `replan-today` re-runs the whole deterministic plan rather than patching just
  today's day; reason-aware venue swapping needs richer venue attributes.
- Days within one city can repeat the same optimized venues (the curated fixture
  set has 4–5 venues per city); real provider data diversifies this.
- The PDF export is a dependency-free one-page latin-1 writer; Persian text needs
  the designed export (the ICS export serves fa users meanwhile).
- Metrics/rate limits are in-process until Redis lands; password hashes live in
  the user preferences JSON pending a dedicated credential table (PBKDF2 itself
  is production-grade); no refresh tokens yet.
- The map widget, SSE progress streaming, the web checklist/expense screens and
  Jalali date rendering are designed-but-not-built UI items.

## 6. Exact commands

```bash
# install
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev,api]"
copy .env.example .env                              # set JWT_SECRET at minimum

# run (offline demo mode - no keys)
set LLM_PROVIDER=mock
uvicorn travel_planner.api.app:app --port 8000
cd web && npm ci && npm run build && npm start

# gates
ruff check src tests scripts
mypy
pytest -q -m "not live"
pytest -m live                                       # needs the gateway key
npx playwright test                                 # from web/
python evaluation/runner.py                         # PYTHONPATH=src;.

# docker (build NOT verified here - see section 4)
export JWT_SECRET=<long random string>
docker compose up --build

# mcp
python -m travel_planner.mcp.server
```

## 7. Required environment variables

Everything is documented in `.env.example`. Mandatory outside local dev:
`JWT_SECRET` (long random), and for anything beyond demo mode `LLM_PROVIDER`,
`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`. Optional but recommended:
`DATABASE_URL` (Postgres), `REDIS_URL`, `ADMIN_BOOTSTRAP_EMAIL`,
`GUEST_TRIAL_ENABLED`, the `<CAPABILITY>_PROVIDERS` chains.

## 8. Go-to-market checklist (for the owner)

1. **Legal review** (blocked on you): privacy policy + ToS (templates are
   marked "needs legal review"), sanctions/compliance for Iran mode, and the
   robots/ToS sign-off per candidate scraping site (`docs/data-sources.md`).
2. **Payments onboarding**: Stripe test keys → live keys, and the Zarinpal
   merchant id; then set `BILLING_ENABLED=true`.
3. **Data licensing** for any curated Iran dataset imported from third parties.
4. **Hosting**: Docker images are ready to build; decide the Postgres/Redis
   hosting and point `DATABASE_URL`/`REDIS_URL` at it.
5. **Scraper approval**: no real site is scraped today; approve specific sites
   via the checklist in `docs/data-sources.md`.
6. **Pricing**: the tier limits are config (`FREE_TIER_PLANS_PER_MONTH`,
   `PRO_TIER_PLANS_PER_MONTH`); set them to the business decision.
7. **Before launch**: run the full gates (`ruff`, `mypy`, `pytest`, Playwright,
   `evaluation/runner.py`), then a live-gateway evaluation run for real token
   and cost numbers.

