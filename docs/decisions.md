# Decision Log (ADR-style)

Each entry: **Decision** / **Alternatives considered** / **Why**.

---

## ADR-001 - One git branch per phase, merged to main after a green gate

**Status:** Accepted

**Decision:** Every phase runs on `phase/<n>-<slug>`. The gate is: run tests/lint/types, write
`STATUS-P<n>.md`, commit with conventional commits, push the branch, merge into `main`, push `main`.
A phase is not complete until its gate is green.

**Alternatives considered:**
- Commit straight to `main` - faster, but a half-finished phase leaves `main` broken.
- Tag-only - weaker history, harder to revert a single phase.

**Why:** The user explicitly chose the branch workflow. It keeps `main` always deployable, makes a
failed phase trivially revertible, and produces a phase-by-phase audit trail in the repository
itself, which matches the master prompt's "work in milestones, one at a time" rule.

---

## ADR-002 - Migrate orchestration from AutoGen to LangGraph

**Status:** Accepted

**Decision:** Replace AutoGen with LangGraph (`langgraph 1.2.12`, verified installable on Python
3.13). The prototype is preserved as `legacy_prototype/` during Phases 0-3 and deleted in Phase 4.

**Alternatives considered:**
- *Keep AutoGen* - already installed and the existing prototype uses it. Rejected: the team is driven
  by a chat transcript; resumable typed state, checkpointing and a first-class trace would all have
  to be hand-built, and the selector protocol is string-matching (audit bug B7).
- *LangChain LCEL chains* - rejected: no native checkpointed cycle for the critic/replanner loop.
- *Hand-rolled state machine* - viable but re-implements checkpointing, retries and parallelism.

**Why:** LangGraph gives exactly what the master prompt demands: a typed `TravelState` persisted
per node, conditional edges for the deterministic routing the prototype already approximates with
`selector_func`, built-in checkpointers (SQLite now, Postgres later) for resumability, and parallel
branches for the nine research agents. The graph is a plain Python object, so it is unit-testable
with no network. The LLM layer stays provider-agnostic, so this decision does not lock in a model vendor.

---

## ADR-003 - Use an OpenAI-compatible gateway (apmix) as the default model provider

**Status:** Accepted

**Decision:** The default development/test gateway is
`https://api.apmix.ai/v1` with model `deepseek/deepseek-v4-flash-free`, selected through
`LLM_PROVIDER=apmix`. Providers `openai`, `openai_compatible`, `ollama` and `mock` are also
supported by the same factory interface.

**Live verification (2026-10-02):** model listing `200`; chat completion `200`; vendor-prefixed
alias `200`; **tool calling `200` with `finish_reason=tool_calls`**; **JSON mode `200` with valid
JSON**. The gateway emits a `reasoning_content` field and sometimes **parallel tool calls**.

**Alternatives considered:**
- *Keep Gemini* - the prototype's key is present, but Gemini is not reachable from Iran and the
  `extra_body.reasoning` extras do not apply to this gateway.
- *Local Ollama only* - maximum privacy but far weaker JSON/tool adherence for a schema-heavy product.

**Why:** The user supplied this key/model explicitly for testing. OpenAI-compatible means one client
implementation covers apmix, OpenAI, OpenRouter-compatible endpoints and Ollama. `mock` guarantees the
app runs end-to-end with zero keys, as the master prompt requires.

**Consequences:** strip `reasoning_content` at the client boundary (no chain-of-thought in the UI);
cap concurrent tool calls per turn; drop Gemini-only request extras.

---

## ADR-004 - `src/` layout, prototype quarantined in `legacy_prototype/`

**Status:** Accepted

**Decision:** All new product code lives under `src/travel_planner/`. The existing top-level
prototype moves to `legacy_prototype/` in Phase 1 and is deleted in Phase 4.

**Alternatives considered:**
- *Evolve the flat layout in place* - keeps git history simple but keeps the Iran/TOMAN hard-coding
  and the Gemini coupling in the import graph forever.
- *Big-bang rewrite into a new repository* - rejected, history and the working validator are valuable.

**Why:** A clean import boundary makes `mypy` and `ruff` meaningful and lets the prototype be
deleted without touching product code. Quarantining rather than rewriting preserves the audit trail.

---

## ADR-005 - SQLite fallback for tests; PostgreSQL for production

**Status:** Accepted

**Decision:** All database access goes through SQLAlchemy async. `DATABASE_URL` selects the backend.
The test suite runs on `sqlite+aiosqlite` so it needs no daemon; Docker Compose provides PostgreSQL
for real deployments. Redis is likewise optional, with an in-process cache fallback.

**Alternatives considered:**
- *PostgreSQL only* - rejected: the Docker daemon is not running in the dev environment, so the
  suite could not be executed, which breaks the "verified by running" rule.
- *SQLite only, no Postgres* - rejected: the master prompt explicitly requires PostgreSQL + Alembic.

**Why:** It satisfies both constraints: real Postgres in production, and a test suite that anyone
can run with `pytest` alone.

---

## ADR-006 - Scraping-first, API-ready provider architecture

**Status:** Accepted

**Decision:** Every data capability is a `Protocol` with an ordered fallback chain selected from env
(`HOTELS_PROVIDERS=scraper_a,curated,estimator`). Implementations are `scraper_*` (current),
`api_*` (reserved, disabled), `curated_dataset`, and `estimator`. A shared `ScraperClient` enforces
robots.txt, rate limits, caching, conditional requests, circuit breakers, sanitization and SSRF
safety. No provider is allowed to invent data: unavailable means `status: unavailable`.

**Alternatives considered:**
- *Official paid APIs first* - rejected, no partner API or budget exists yet.
- *Free-text LLM research only* - rejected, unverifiable and unsourceable.

**Why:** The commercial value depends on hotels/transport data that has no accessible API. Building
against interfaces from day one means a future official API replaces a scraper by changing one env
line, without touching agents, tools, schemas or UI. Responsible-scraping rules live in the shared
client, not in each scraper, so they cannot be forgotten in a new provider.

---

## ADR-007 - The agent never books or pays

**Status:** Accepted

**Decision:** The system produces a "Booking Assistant" step: shortlist, estimate, human confirmation,
then a redirect or deep link to the provider's own page with prefilled dates/guests where the URL
format allows. `BookingProvider` implements only `redirect`; `api_booking` is reserved.
Affiliate IDs come from env, clicks are tracked, and sponsored results are disclosed.

**Alternatives considered:**
- *Integrate a booking/payment API* - rejected, no partnership exists and it would add heavy
  compliance and PCI scope.

**Why:** Required by the master prompt, and it keeps the product free of payment-card handling while
still capturing affiliate revenue. It also keeps the user in control of the actual transaction.

---

## ADR-008 - Deterministic code beats LLM calls for optimization and validation

**Status:** Accepted

**Decision:** Geographic clustering, route ordering (nearest-neighbour + 2-opt), opening-hours and
budget feasibility, daily workload caps, and currency conversion are computed in Python from real
coordinates and travel times. The LLM is used only for selection, narrative and intent parsing.
Structural and semantic validation is code, never a model.

**Alternatives considered:**
- *Ask the LLM to build the itinerary* - rejected, this is what the prototype does and it produces
  infeasible days, duplicated POIs and backtracking.

**Why:** Deterministic results are testable, reproducible and cheap. This is also the core
differentiator: "deterministic optimization" versus vague LLM suggestions.

---

## ADR-009 - No phase gate is skipped, and unverified work is labelled

**Status:** Accepted

**Decision:** Each phase ends with a `STATUS-P<n>.md` that separates **Verified** (actually executed)
from **Implemented, not verified** (needs a key, network or Docker). No fake integrations, no silent
stubs; where a real API is unavailable a clearly named `mock`/`fixture` provider is used and
documented. Known environment limits (Docker daemon down, no `gh` CLI) are stated explicitly.

**Alternatives considered:**
- *Report optimistically and fix later* - rejected, it destroys trust and hides real risk.

**Why:** The master prompt requires honesty as a hard rule. It also protects the owner from making
commercial or legal decisions based on untested claims.
