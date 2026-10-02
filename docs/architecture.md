# Target Architecture

Status: **target state**. The implementation reaches it incrementally, phase by phase
(see `plan-mode-cline.md`). Items marked *(phase N)* land in that phase.

---

## 1. Shape

A **modular monolith**. One deployable API, one web app, one Postgres. No microservices, no vector
database, no message broker beyond a Redis-backed job queue.

```text
                    +---------------------------+
   Browser  <---->  |   Next.js web app (web/)   |   RTL fa/en, map, PWA Live Mode
                    +-------------+-------------+
                                  |  REST /api/v1 + SSE
                    +-------------v-------------+
                    |   FastAPI application     |   auth, quotas, SSE, export
                    +------+-------------+------+
                           |             |
              +------------v--+       +--v-------------------+
              |  LangGraph app |       |  Background workers  |  long plans, canary
              |  TravelState   |       |  (Redis / in-proc)   |
              +---+----+----+--+       +--+-------------------+
                  |    |    |             |
        +---------v-++-v-++-v--+  +-------v--------+
        | agents   | llm | tools|  | providers/<cap> |
        | (nodes)  |     |      |  | scraper/curated |
        +-----+----+--+--+------+  | estimator/api   |
              |    |     |         +----------------+
              |    |     |
        +-----v----v-----v-----------+
        |  Postgres  |  Redis cache  |
        +-------------+--------------+
```

---

## 2. Backend package layout *(phases 1-4)*

```text
src/travel_planner/
  config/           settings (typed, env-driven), RegionProfile, feature flags
  schemas/          TripRequest, TravelState, Itinerary, Finding, PlaceInfo,
                    HotelOffer, TransportOption, PriceEstimate, EntryRequirement ...
  llm/              provider-agnostic model factory + token accounting
  agents/           intent, supervisor, research_*, planner, validator, critic,
                    replanner, writer, edit_handler  (each a graph node)
  graph/            build_graph(), nodes/, edges/, checkpointer setup
  optimizer/        clustering, routing (2-opt), scheduling, budget solver  (pure, no LLM)
  tools/            typed tool wrappers with timeout, retry, source metadata
  providers/        <capability>/{protocol.py, scraper_*.py, curated.py, estimator.py}
    registry.py     ProviderRegistry, chain selection from env
    http/           ScraperClient: robots.txt, rate limit, cache, breaker, sanitize
  services/         trips, memory, entitlement, usage, affiliate, booking, export,
                    analytics, notifications
  db/              models, session, repositories, migrations (Alembic)
  api/              FastAPI routers, deps, SSE, error envelopes
  cli.py            python -m travel_planner.cli
evaluation/         scenarios + metrics + report generation
web/                Next.js app
legacy_prototype/   AutoGen spike, deleted in phase 4
```

---

## 3. Orchestration *(phase 2)*

`TravelState` is a Pydantic model and the single source of truth. Nodes are plain async functions;
edges are explicit and conditional. Checkpoints are written after every node.

```text
intent -> clarify -> supervisor
  supervisor -> research fan-out (places, weather, routes, hotels, restaurants,
                                transport, events, currency, entry)
             -> merge_findings
             -> plan (optimizer first, LLM for selection/narrative)
             -> validate
                  invalid & repair_loops < MAX -> critic -> replanner -> validate
                  valid or budget exhausted    -> write -> END
edit path: message -> parse_constraints -> patch_state
           -> re-run only the affected research nodes -> validate -> write
```

Rules:

- **No node may call an LLM to compute something deterministic.** Routes, hours, budgets and
  currency conversion are pure Python (ADR-008).
- **Every node is idempotent** and safe to re-run after a checkpoint restore.
- **The trace is data, not prose**: each node appends `AgentRun{node, started_at, ended_at,
  status, inputs_digest, outputs_digest, tokens, tools_used}`. `reasoning_content` from the model
  is discarded and never persisted.
- **Bounded loops**: `MAX_REPAIR_LOOPS` (config). On exhaustion the planner returns best-effort
  output plus explicit warnings.

---

## 4. Data flow for a single plan

```text
user text
  -> IntentAgent        -> TripRequest + assumptions + clarifying questions
  -> region profile     -> IRAN | INTERNATIONAL (providers, currency, calendar, language)
  -> research fan-out   -> Findings[], each with source, retrieved_at, confidence, status
  -> optimizer          -> day assignment, route order, feasibility, budget split
  -> Planner (LLM)      -> narrative + selection within the optimizer's constraints
  -> Validator          -> structural (Pydantic) + semantic (dates/hours/feasibility/budget)
  -> Critic/Replanner   -> targeted repair, max N loops
  -> Writer             -> user-facing text with sources and confidence labels
```

Everything above runs identically offline when `LLM_PROVIDER=mock` and the provider chains point at
`fixture`/`curated` datasets.

---

## 5. Provider layer *(phase 3)*

```text
capability Protocol
  |-> scraper_*        current, responsible scraping, behind the shared ScraperClient
  |-> api_*            reserved for official APIs, config + contract tests, disabled
  |-> curated_dataset  JSON/CSV with last_verified_at + admin import
  |-> estimator        formula-based fallback, always labelled "estimated"
  `-> fixture          recorded responses for offline tests
```

Chain selection is configuration, not code:

```dotenv
HOTELS_PROVIDERS=scraper_site_a,curated,estimator
TRANSPORT_PROVIDERS=curated,estimator
RIDE_FARE_PROVIDERS=estimator
```

A provider returns `status: unavailable` rather than inventing data. The registry records which
provider answered, so the UI can always show "source, retrieved at, confidence".

**Responsible scraping** is enforced centrally by `ScraperClient`: robots.txt check, identifiable
User-Agent with a contact URL, <=1 request/2s per domain, jitter, exponential backoff,
`Retry-After` handling, caching with per-type TTLs, conditional requests, per-source circuit
breaker, HTML sanitization and prompt-injection filtering, SSRF-safe URL validation. Logins,
paywalls, CAPTCHAs and IP blocks are never bypassed; no proxy rotation or fingerprint spoofing.

---

## 6. Persistence *(phase 4)*

PostgreSQL via SQLAlchemy async + Alembic. `sqlite+aiosqlite` is the test/dev fallback (ADR-005).

Tables: `users`, `subscriptions`, `usage_events`, `trips`, `trip_messages`, `trip_preferences`,
`itineraries`, `itinerary_days`, `places`, `sources`, `agent_runs`, `tool_runs`, `share_links`,
`affiliate_clicks`.

Redis: response cache (TTL by data type), rate-limit counters, job state, SSE pub/sub. An
in-process cache is used when Redis is absent so the app degrades instead of failing.

**Memory layers** (all user-visible, editable and deletable):

| Layer | Scope | Content |
|---|---|---|
| Conversation memory | per trip | recent turns, used for follow-up edits |
| Trip memory | per trip | validated findings, itinerary versions, sources |
| User preference memory | per user | travel pace, food, transport, budget style |

---

## 7. API surface *(phase 4)*

```text
POST   /api/v1/trips                     create a trip (natural language)
GET    /api/v1/trips                     list
GET    /api/v1/trips/{id}                detail
POST   /api/v1/trips/{id}/messages       conversational edit
POST   /api/v1/trips/{id}/replan         one-tap re-plan today
GET    /api/v1/trips/{id}/stream         SSE: progress + agent trace
GET    /api/v1/trips/{id}/trace          agent trace
GET    /api/v1/trips/{id}/sources        source drawer data
POST   /api/v1/trips/{id}/share          create public share link
GET    /api/v1/share/{token}             public read-only trip page
GET    /api/v1/trips/{id}/export.pdf     PDF export
GET    /api/v1/trips/{id}/export.ics     calendar export
GET    /api/v1/usage                     usage + entitlements
POST   /api/v1/billing/webhook           provider webhooks (idempotent)
GET    /health  /ready                   health and readiness
```

Errors are a single envelope: `{ "error": { "code", "message", "request_id", "details" } }`.
Every response carries a request ID, which also appears in the structured logs.

---

## 8. Frontend *(phase 5)*

Next.js (App Router) + TypeScript + Tailwind. i18n `fa`/`en` with full RTL, Persian digits and
Jalali/Gregorian calendars. Map via Leaflet (no API key needed; OSM tiles). PWA service worker
caches the itinerary for offline Live Mode. Dark mode, loading/error/empty states everywhere,
accessible by keyboard and screen reader.

---

## 9. Security posture

- Secrets only from env; `.env` is git-ignored and `.env.example` carries no real values.
- SSRF protection on every outbound fetch (scheme/host allowlist, private-IP blocking, redirect limits).
- Untrusted web content is sanitized and prompt-injection-filtered before reaching any LLM.
- No tool execution is ever driven by fetched page content.
- Rate limiting per user/IP; CORS allowlist; safe HTML rendering (no raw model HTML).
- GDPR-style data export and delete; privacy policy and ToS templates marked "needs legal review".
- No card data is ever stored; payments run in provider test mode only.

---

## 10. Observability

Structured JSON logs (no secrets, no PII), OpenTelemetry-compatible spans per node and per tool call,
and metrics for latency, token usage, estimated cost, retries, circuit-breaker state and error rate.
Cost per itinerary is computed from recorded token counts and a configurable price table.
