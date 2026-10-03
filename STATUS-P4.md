# STATUS - Phase 4 (Persistence and API)

Date: 2026-10-03
Branch: `phase/4-api-db`
Gate: API end-to-end tests green. **Passed.**

---

## Done

- [x] `travel_planner.db.models` - the full schema from the master prompt, all
      14 tables: `users`, `subscriptions`, `usage_events`, `trips`, `trip_messages`,
      `trip_preferences`, `places`, `sources`, `itineraries`, `itinerary_days`,
      `agent_runs`, `tool_runs`, `share_links`, `affiliate_clicks`.
      Auth/billing tables exist from day one with a nullable user (ADR-05);
      nested product data is stored as JSON typed at the Pydantic boundary.
- [x] `travel_planner.db.session` - async SQLAlchemy engine + session factory,
      SQLite fallback (ADR-05), `create_all` for zero-setup demo mode, lazy
      per-URL engine caching, plain-sqlite URL normalization.
- [x] `travel_planner.services.trips` - the bridge between API, graph and DB:
      create/get/list trips, messages, the latest itinerary (versioned history,
      never overwritten), agent-run persistence (structured steps only, never
      chain-of-thought), usage events, warnings stored as messages.
- [x] `travel_planner.api.app` - FastAPI with:
      one error envelope `{error: {code, message, request_id, details}}`,
      `X-Request-ID` on every response, per-IP rate limiting (in-process now,
      Redis behind the same interface later), access logs with latency.
- [x] Routers:
      - `POST /api/v1/trips` - create + plan inline (the graph is deterministic
        and fast offline), persisting itinerary, days, trace, message, usage
      - `GET /api/v1/trips`, `GET /api/v1/trips/{id}` (list/detail)
      - `GET /api/v1/trips/{id}/itinerary` (latest version + payload)
      - `GET /api/v1/trips/{id}/messages`, `GET .../trace`
      - `POST /api/v1/trips/{id}/replan` (new version, history kept)
      - `POST /api/v1/trips/{id}/share` + `GET /api/v1/share/{token}`
        (public read-only; idempotent token)
      - `GET /api/v1/usage` (aggregated by kind, quotas shown)
      - `GET /api/v1/health`, `GET /api/v1/ready`
- [x] **`legacy_prototype/` and the old AutoGen top-level code deleted** as
      planned: `agents/`, `config/settings.py` (old), `models/`, `teams/`,
      `tools/`, `utils/`, `main.py`. AutoGen is fully out of the product code.
- [x] 15 API e2e tests (httpx ASGI transport, real graph, throwaway SQLite).

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 52 files) | **Success: no issues found** |
| Offline tests | `pytest -q -m "not live"` | **164 passed** |
| **Gate: API e2e** | `pytest tests/integration/test_api.py` | **15 passed** |
| Phase 2 CLI gate | `travel-planner plan --demo --nights 3` | exit 0 |

The e2e suite exercises the real golden path over HTTP: create a trip -> the
graph plans it -> the itinerary is stored valid with 3 days -> the assistant
message exists -> the trace has >= 4 steps -> replan creates version 2 while
keeping version 1 -> share link round-trips read-only -> usage is recorded ->
bad ids get the envelope with a request id -> the rate limiter returns 429.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| PostgreSQL + asyncpg | no Postgres in this environment (declared limitation) | `docker compose up postgres` then `DATABASE_URL=postgresql+asyncpg://...` |
| Alembic migrations | the schema is created by `create_all` at startup; Alembic is installed and configured for phase 6+ when schema evolution begins | `alembic init` + first revision, then `alembic upgrade head` |
| Redis cache / rate limits | not installed here; the in-process implementations are correct and behind interfaces | `docker compose up redis` |
| SSE streaming of progress | the inline plan runs in well under a second offline, so streaming adds nothing yet; the endpoint shape is reserved | phase 5 with the web UI |
| Background job queue | same reason - the offline graph is fast; live providers will need it | phase 5+ |

## Known limitations (honest)

- The plan currently runs inline in the request. With live providers this must
  move to a background job + SSE; the routes stay the same.
- Rate limiting is per-process; a second worker doubles the effective limit
  until Redis lands.
- `agent_runs` currently records summary steps; per-node token accounting
  starts when the graph's nodes return usage (the LLM layer already counts it).
- Windows note: the OS temp directory is not writable in this environment, so
  the API tests use a project-local `.pytest_tmp` directory.

## Decisions taken

- **The lifespan creates the schema** for the app's own `state.database_url`,
  never the ambient settings - a test app must never touch the default database.
  (Found the hard way by an e2e failure; fixed and covered by tests.)
- **Itinerary versions are append-only.** `replan` writes a new version; the old
  one is history. A plan history is a product feature, not a side effect.
- **Warnings are messages.** Validation warnings are persisted as assistant
  messages so they are visible to the user, not only in logs.

## Next - Phase 5 (Web application)

1. Next.js + TypeScript + Tailwind in `web/`, App Router.
2. i18n fa/en with full RTL, Persian digits, Jalali+Gregorian dates.
3. Screens: Landing + pricing, chat-style request, planning progress,
   Itinerary (day tabs, timeline, map, costs, warnings, sources drawer with
   confidence labels), trace panel, history, share page.
4. Talks to the phase 4 API; no direct graph access.
5. Gate: Playwright golden path - create trip -> edit -> share.
