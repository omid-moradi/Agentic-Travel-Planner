# Agentic Travel Planner - Execution Plan (Phases 0 to 9)

> Status: **ACTIVE** - plan approved, execution started on branch `phase/0-audit`
> Repository: `https://github.com/omid-moradi/Agentic-Travel-Planner`
> Product scope source of truth: `travel-planner-master-prompt.md` (v2, commercial product)

---

## 1. Objective

Turn the existing AutoGen prototype (Researcher, Planner, Writer, Validator) into a
**revenue-ready SaaS** that plans and manages an **entire trip**, for **domestic Iran trips and
international trips**, in **Persian (RTL) and English**.

The product covers the full trip lifecycle:

- **Before the trip** - natural-language request to a typed `TripRequest`, destination research,
  day-by-day itinerary, budget breakdown, hotels and transport, packing list, document checklist,
  entry requirements (international), seasonal and weather-aware planning.
- **During the trip ("Live Mode")** - today's plan, offline-friendly PWA, one-tap "Re-plan today",
  expense tracker with currency conversion and budget burn-down.
- **After the trip** - trip summary, expense split between travelers, shareable public trip page,
  PDF and ICS export.

Core differentiators that must be genuinely implemented:

1. **Source-grounded facts** - every fact carries `confirmed / estimated / inferred / unavailable`.
2. **Deterministic optimization** - routes, opening hours, budget (never LLM-guessed).
3. **Conversational edits** - patch only the affected parts, then revalidate.
4. **Transparent agent trace** - structured steps, never chain-of-thought.

---

## 2. Target LLM Gateway (verified live)

The model layer is **provider-agnostic**. For development and testing we use an OpenAI-compatible
gateway:

```dotenv
LLM_PROVIDER=apmix
LLM_BASE_URL=https://api.apmix.ai/v1
LLM_API_KEY=apx_live_...          # stored ONLY in .env (git-ignored, never committed)
LLM_MODEL=deepseek/deepseek-v4-flash-free
LLM_TEMPERATURE=0.4
LLM_TIMEOUT=60
LLM_MAX_TOKENS=4096
```

**Verified capabilities (live probes, 2026-10-02):**

| Capability | Probe | Result |
|---|---|---|
| Model listing | `GET /v1/models` | `200` - `deepseek-v4-flash-free` |
| Chat completion | `POST /v1/chat/completions` | `200` OK |
| Vendor-prefixed alias | `model=deepseek/deepseek-v4-flash-free` | `200` OK |
| Tool / function calling | `tools=[web_search]` | `200`, `finish_reason=tool_calls` OK |
| JSON mode | `response_format={"type":"json_object"}` | `200`, valid JSON OK |

Notes:

- Responses include a `reasoning_content` field. It is **dropped at the model-client boundary**
  and never surfaced to users (no chain-of-thought in the UI).
- The gateway emits **parallel tool calls**. The tool layer must be idempotent and must cap
  concurrent calls per turn.
- Gemini-specific extras (`extra_body.reasoning`) from the prototype are **removed** - they are
  not valid for this gateway.

Supported providers (selected through `LLM_PROVIDER`): `apmix`, `openai`, `openai_compatible`,
`ollama`, and `mock` (offline demo mode, zero network).

---

## 3. Orchestration Decision - LangGraph replaces AutoGen

**Decision: migrate from AutoGen to LangGraph.**

LangGraph 1.2.12 is available for Python 3.13 and was verified installable in this environment.
Reasons:

1. **Typed, explicit state** - `TravelState` is a Pydantic model persisted per node, which is
   exactly what the master prompt requires for resumable, checkpointed workflows.
2. **Deterministic control flow** - a real state machine (nodes plus conditional edges) instead of
   an LLM selector. The prototype already uses a code-based `selector_func`; LangGraph makes that
   first-class, testable and inspectable, which is what the agent-trace feature needs.
3. **Checkpointing built in** - `langgraph-checkpoint` supports SQLite and Postgres savers, so
   resumability and crash recovery come from the framework rather than bespoke code.
4. **Parallel research fan-out** - parallel branches map directly to the nine research agents.
5. **No hidden magic** - the graph is a plain Python object, fully unit-testable without network.

AutoGen is preserved as `legacy_prototype/` for reference during Phases 0 to 3 and is deleted in
Phase 4. Full rationale recorded in `docs/decisions.md` (ADR-002).

### Target graph shape

```text
START
  -> intent -> clarify -> supervisor
                               |
                               +-> research (parallel: places, weather, routes, hotels,
                               |              restaurants, transport, events, currency, entry)
                               |        -> merge_findings
                               |
                               +-> plan (deterministic optimizer + LLM selection and narrative)
                               |        -> validate
                               |              +-- invalid and loops < N -> critic -> replan --+
                               |              +-- valid ------------------------------------+
                               |                                                             |
                               +-------------------------------------------------------------+
                                                      -> write -> END

  Conversational edit path:
      message -> parse_constraints -> patch_state
               -> [resume only affected research nodes] -> validate -> write
```

---

## 4. Repository Strategy

One branch per phase. No phase starts until the previous phase's gate is green.

```text
main  -+- phase/0-audit        -> merge -> main
       +- phase/1-core         -> merge -> main
       +- phase/2-agents       -> merge -> main
       +- phase/3-providers    -> merge -> main
       +- phase/4-api-db       -> merge -> main
       +- phase/5-web          -> merge -> main
       +- phase/6-monetization -> merge -> main
       +- phase/7-whole-trip   -> merge -> main
       +- phase/8-obs-eval-mcp -> merge -> main
       +- phase/9-devops       -> merge -> main
```

### Per-phase gate (non-negotiable)

```text
1. run tests / lint / types
2. write STATUS-P<n>.md   (done / verified / NOT verified / next)
3. git commit   (conventional commits)
4. git push     (phase branch)
5. merge into main
6. git push     (main)
```

If the gate fails, the phase is not marked complete and the next phase does not start.

### Honesty policy

- Never claim something works unless it was actually executed.
- Every deliverable is labelled **Verified** (ran it) or **Implemented, not verified**
  (needs API key / network / Docker).
- No fake integrations, no silent stubs. Where a real API is unavailable, a clearly named
  `mock` / `fixture` provider is used and documented as such.

---

## 5. Phase Breakdown

### Phase 0 - Audit and Plan (current)

Deliverables:

- `docs/audit.md` - reusable parts, bugs, tech debt and risks of the existing prototype.
- `docs/decisions.md` - ADR-style decision log (decision / alternatives / why).
- `docs/architecture.md` - target architecture and package layout.
- `.env.example` - every variable documented, **no real secrets**.
- `README.md` - skeleton with honest "work in progress" status.

Gate: docs committed and `git push` to GitHub succeeds.

---

### Phase 1 - Core foundation and apmix migration

Deliverables:

- `.env` migrated to the apmix gateway; `config/settings.py` stops hard-failing on `GOOGLE_API_KEY`.
- `src/travel_planner/config/` - env-driven typed settings, no import-time side effects.
- `src/travel_planner/llm/` - provider-agnostic model factory
  (`apmix | openai | openai_compatible | ollama | mock`), correct `ModelInfo`,
  reasoning-content stripping, retry/timeout, token accounting.
- `pyproject.toml` with pinned dependencies; `ruff` + `mypy` + `pytest-cov` configured.
- Rebuild the broken `.venv` (it currently points at a stale path `F:\AgenticAI\...`).
- Prototype moved to `legacy_prototype/`; new `src/travel_planner/` skeleton created.
- Fix the two currently-broken prototype tests; add a real live smoke test against apmix
  (auto-skipped when the key or network is absent).

Gate: `ruff check` OK, `mypy` OK, `pytest` OK, and a live call returns `200`.

---

### Phase 2 - Agentic core and optimizer

Deliverables:

- Typed `TravelState` (Pydantic) + checkpoint saver.
- `IntentAgent` -> validated `TripRequest` + assumptions + high-value clarifying questions.
- `Supervisor` -> mostly deterministic routing, parallel research, retries, termination,
  human-confirmation gates.
- Nine parallel research nodes: places, weather, routes, hotels, restaurants, transport,
  events, currency/budget, entry requirements.
- `Planner` + **deterministic optimization engine**: geographic clustering, route ordering
  (nearest-neighbour + 2-opt), opening-hours/budget constraints, daily workload caps,
  required/forbidden items. Real coordinates and travel times only.
- `Validator` (structural Pydantic + semantic: dates, opening hours, travel-time feasibility,
  budget totals, duplicate POIs, daily load).
- `Critic` (structured issues + severity) -> `Replanner` (targeted repair, max N loops) ->
  best-effort result with warnings.
- `Writer` - polished user-facing output with sources and confidence labels, no internal reasoning.
- Edit/chat handler mapping "cheaper", "remove museums", "rain on day 3", "add a day" to
  constraint patches, re-running only affected nodes.
- **Demo mode** with fixtures, fully offline.
- CLI: `python -m travel_planner.cli plan --demo`.

Gate: the CLI plans a valid Tehran to Shiraz trip **offline**.

---

### Phase 3 - Data providers (scraping-first, API-ready)

Deliverables:

- `providers/<capability>/` per capability: `Protocol` interface + `scraper_*` (current),
  `api_*` (future, config + contract tests, disabled), `curated_dataset`, `estimator`.
- `ProviderRegistry` driven by env, e.g. `HOTELS_PROVIDERS=scraper_site_a,curated,estimator`.
  Swapping a scraper for an official API = changing one env line.
- Shared `ScraperClient` enforcing: robots.txt compliance, identifiable User-Agent,
  per-domain rate limiting (<=1 req/2s), jitter, exponential backoff, `429/Retry-After` honouring,
  aggressive caching (TTL: prices hours / place info days), conditional requests
  (ETag / If-Modified-Since), per-source circuit breaker, sanitization of untrusted content,
  prompt-injection filtering before any LLM sees it, SSRF-safe fetching.
- Extraction stack in order of preference: official feeds (sitemap/RSS/JSON-LD/OpenGraph/public
  JSON endpoints, OSM/Overpass, Wikipedia/Wikidata), then static HTML (`httpx` + `selectolax` /
  BeautifulSoup against structured markers), then Playwright only when necessary, then
  LLM-assisted extraction strictly as a fallback parser with schema validation.
- Normalized schemas shared by all providers: `HotelOffer`, `TransportOption`, `PlaceInfo`,
  `PriceEstimate{low, expected, high, currency, basis, confidence, status, source,
  retrieved_at, last_verified_at}`.
- Pricing / ride-fare `estimator` (OSRM distance and time x per-city calibrated formula
  `base + per_km + per_minute x time_of_day_multiplier`), editable calibration dataset,
  admin "submit a real fare sample", results always labelled **estimated**.
- Maps / geocode / routing (Nominatim/OSRM/Valhalla, Neshan/Balad adapter slot behind env key),
  Open-Meteo weather, currency, public holidays, POIs.
- Booking assistant: shortlist -> estimate -> user confirms -> redirect / deep link with prefilled
  dates and guests. The agent **never books or pays**.
- Parser contract tests with saved HTML fixtures (`tests/fixtures/html/`) + nightly canary job.
  Every result carries `parser_version`; garbled records are rejected, not passed through.
- `docs/data-sources.md` (source, method, ToS/robots finding, rate limit, risk, API replacement
  path) and a `SOURCES.md` registry.

Gate: parser contract tests green + documented live smoke tests.

---

### Phase 4 - Persistence and API

Deliverables:

- FastAPI `/api/v1`, async, typed models, structured errors, request IDs, rate limiting,
  auth-ready dependencies, SSE streaming of progress and agent trace.
- Endpoints: trips CRUD, messages, replan, trace, sources, share, export, billing, usage,
  health/ready.
- PostgreSQL + Alembic with the full schema: users, subscriptions, usage_events, trips,
  trip_messages, trip_preferences, itineraries, itinerary_days, places, sources, agent_runs,
  tool_runs, share_links, affiliate_clicks.
- **SQLite/aiosqlite fallback** so tests run without a database daemon; Postgres via compose.
- Redis for cache, rate limits and job state (with in-process fallback).
- Memory layers: conversation memory, trip memory, long-term user preference memory
  (travel pace, food, transport, budget style) - user-visible, editable and deletable.
- `legacy_prototype/` deleted at the end of this phase.

Gate: API end-to-end tests green.

---

### Phase 5 - Web application (Next.js + TypeScript)

Deliverables:

- Polished, accessible, mobile-first UI with loading/error/empty states and dark mode.
- i18n `fa`/`en` with full RTL, Persian digits, Jalali/Gregorian calendars.
- Screens: Landing + pricing, Home (chat-style request), Trip setup with editable assumptions,
  live planning progress (streamed), Itinerary (day tabs, timeline, **map**, costs, weather,
  warnings, source drawer with confidence labels), conversational editing, agent trace panel,
  trip history, Live Mode (PWA, offline cache), expense tracker, share page,
  account/billing/usage, admin dashboard.

Gate: Playwright golden path - create trip, edit, share.

---

### Phase 6 - Monetization

Deliverables:

- Auth and accounts: email + OAuth (Google), JWT/session, roles (user, admin), guest trial
  (1 free plan without signup).
- Plans and quotas: Free / Pro / Team, enforced through a central `EntitlementService` +
  usage metering (plans, replans, tokens, tool calls).
- Payments: `PaymentProvider` interface; Stripe adapter + Iran-compatible adapter
  (Zarinpal/IDPay) behind a feature flag. Webhooks, idempotency, subscription state machine,
  invoices. **Test modes/mocks only - never store card data.**
- Affiliate/referral: every hotel/flight/activity result carries a `booking_url` (redirect only)
  via `AffiliateLinkService`, click tracking, clear sponsored/affiliate disclosure.
- Shareable and viral loop: public read-only trip pages with OG images, "Plan a similar trip" CTA,
  referral credits.
- Admin dashboard: users, usage, cost per plan, conversion funnel, provider health,
  feature flags, data-verification queue.
- Unit economics: log estimated cost per itinerary, enforce per-plan token/tool budgets,
  model routing (cheap for extraction, strong for planning), gross margin per tier.
- Product analytics: privacy-respecting, optional, PostHog-compatible.

Gate: webhook + entitlement tests green.

---

### Phase 7 - Whole-trip features

Deliverables:

- Entry requirements (international): visa/entry rules, passport validity, insurance, health
  notes - always sourced and dated, always with a "verify with official source" warning.
  Never state visa rules as certain without a source.
- Packing list + document checklist.
- Live Mode PWA: today's plan, next-stop navigation, offline cached itinerary,
  one-tap "Re-plan today" (rain, closed venue, running late, tired, budget changed).
- Expense tracker with currency conversion and budget burn-down.
- ICS calendar export + PDF export.

Gate: export tests green; Live Mode replan covered by unit tests.

---

### Phase 8 - Observability, evaluation and MCP

Deliverables:

- Structured logging (no secrets/PII), OpenTelemetry-compatible tracing, metrics for latency,
  tokens, cost, retries, errors, tool calls.
- Cost dashboard per plan.
- **Evaluation harness** (`evaluation/`): 20+ scenarios (Iran domestic, international,
  budget cuts, rain, incomplete requests, multi-city) with metrics for validity,
  constraint adherence, budget accuracy, time feasibility, geographic efficiency,
  source grounding, tool choice, recovery, latency, tokens and cost.
  JSON + Markdown report, reproducible with fixed seeds/fixtures.
- Failure-injection suite: timeout, 429, malformed JSON, provider outage, empty results,
  invalid location, conflicting data, missing weather, planner/critic failure,
  payment webhook replay.
- Optional **MCP server** exposing the same tools + an MCP client abstraction;
  the core app must work without it.

Gate: evaluation report generated with real numbers; failure injection degrades gracefully.

---

### Phase 9 - DevOps and polish

Deliverables:

- Dockerfiles + `docker-compose` (api, web, postgres, redis), health/readiness.
- CI: ruff, mypy/pyright, pytest-cov, frontend lint/test/build, `pip-audit`/`npm audit`,
  pre-commit, pinned dependencies.
- Security: env-only secrets, input/output validation, SSRF protection, rate limiting, CORS,
  dependency audit, safe HTML rendering, GDPR-style export/delete, privacy policy + ToS
  templates marked "needs legal review".
- Accessibility, performance, documentation.
- `README.md` (overview, screenshots, features, architecture, agents, tools, data flow, MCP, API,
  install, env vars, Docker, testing, eval, observability, security, example usage, roadmap,
  limitations) + `docs/{architecture,agents,tools,api,deployment,evaluation,security,
  monetization,iran-mode,data-sources}.md`.
- Final report: what was implemented, architecture, agents, tools, providers, fallbacks,
  DB design, memory design, UI, monetization, MCP, test and eval status **with real numbers**,
  observability, security, exact commands, required env vars,
  **known limitations (explicit about anything unverified)**, and a go-to-market checklist.

Gate: all previous gates still green; final report honest about unverified items.

> **Known environment limitation:** Docker is installed (27.1.1) but the Docker Desktop daemon was
> not running during planning. Phase 9 will either start Docker Desktop or report the compose build
> explicitly as *implemented, not verified*.

---

## 6. Market Modes

`RegionProfile` is config-driven and selects providers, currency, calendar, language and data
sources per trip. No global provider assumptions.

**Iran mode** - Jalali (Shamsi) + Gregorian calendars, Persian digits, RTL, IRR/Toman toggle
(Toman = IRR/10, always labelled); OpenStreetMap-based maps stack (Nominatim/OSRM/Valhalla,
self-hostable) with an adapter slot for Neshan/Balad behind an env key; intercity transport and
hotels via permitted, rate-limited, cached paths or curated/manual datasets with
`last_verified_at`; connectivity designed so the core app runs on self-hostable/open components
with a configurable model gateway (apmix / OpenAI-compatible / local Ollama); Persian cuisine and
dietary preferences, prayer/closing times, public holidays and Nowruz peak seasons, cultural and
dress notes, local price levels. Sanctions and compliance considerations documented for legal review.

**International mode** - OSM + optional Google/Mapbox, Open-Meteo, Amadeus/Duffel-style or
affiliate flight/hotel search, exchange-rate API, public-holiday API, OpenTripMap/Foursquare/
Overpass; walking-first city-break itineraries; multi-city trips.

**Provider rules (both modes)** - every capability has a `Protocol`, a fallback chain,
retry + exponential backoff + timeout + circuit breaker, Redis cache with TTLs, and a
graceful-degradation result (`status: unavailable`, never invented data). All keys via env vars;
the app must run end-to-end in **demo mode with zero paid keys**.

---

## 7. Ground Rules (carried from the master prompt)

1. **Audit before coding.** Done in Phase 0.
2. **Milestones one at a time**, gates enforced, conventional commits, short status reports.
3. **Be honest.** Verified vs. implemented-but-unverified is always separated.
4. **Decide, don't ask.** Reasonable choices are made and recorded in `docs/decisions.md`.
   The user is asked only for genuinely blocking items (secrets, legal/business choices).
5. **No overengineering.** Modular monolith. No microservices, no vector DB, no extra agents
   without an ADR. Deterministic code beats LLM calls wherever possible.
6. **The agent never books or pays.** It proposes; the human reviews, confirms and completes
   the transaction on the provider's own page.

---

## 8. Definition of Done (final)

- All ten phase gates green.
- `pytest` (unit + integration + e2e) green; Playwright golden path green.
- Evaluation report with 20+ scenarios and real metrics committed.
- Demo mode plans a full trip offline with zero external calls.
- `README.md` + all `docs/*.md` complete, with limitations stated explicitly.
- Repository pushed to `https://github.com/omid-moradi/Agentic-Travel-Planner`.

---

*Last updated: Phase 0 - see `STATUS-P0.md` for the phase report.*
