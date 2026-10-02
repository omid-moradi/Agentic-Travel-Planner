# Audit - Agentic Travel Planner (Phase 0)

Audit date: 2026-10-02
Audited commit: `81f7431` ("refactor(team): Implement deterministic workflow with SelectorGroupChat")
Auditor: Cline (AI agent), reviewed with the repository owner.

---

## 1. What exists today

The repository is an **AutoGen prototype**, not a product. It is 11 Python files:

| Path | Lines | Purpose |
|---|---|---|
| `main.py` | 55 | CLI entry point; hard-codes one Persian task (Hamedan, 11 Shahrivar 1404) |
| `teams/travel_team.py` | 139 | `SelectorGroupChat` with a code-based `selector_func` |
| `agents/researcher.py` | 48 | LLM agent with the Tavily `web_search` tool, outputs a `ResearchReport` JSON |
| `agents/planner.py` | 72 | LLM agent, outputs an `ItineraryPlan` JSON, all costs in TOMAN |
| `agents/writer.py` | 26 | LLM agent, renders a Persian brief, terminates with the word "پایان" |
| `agents/validator.py` | 64 | **Code-based** (non-LLM) validator of JSON against Pydantic models |
| `models/GoogleModel.py` | 27 | Single hard-wired Gemini `OpenAIChatCompletionClient` |
| `config/settings.py` | 64 | Three dataclasses read from `.env`; raises at import if keys are missing |
| `tools/web_search.py` | 38 | Tavily search wrapper |
| `utils/validation.py` | 49 | Pydantic schemas: `Source`, `Finding`, `ResearchReport`, `ItineraryDay`, `ItineraryPlan` |
| `utils/validation_utils.py` | 35 | `validate_json_with_model` helper |
| `utils/utils.py` | 40 | Termination condition + best-effort JSON state save/load |
| `tests/` | 3 files | `conftest.py`, `agent_test.py`, `test_tools.py` |

Runtime environment (verified): Python 3.13.5, `autogen-agentchat 0.7.4`, `autogen-core 0.7.4`,
`autogen-ext 0.7.4`, `openai 1.100.2`, `pydantic 2.11.7`, `tavily-python 0.7.11`, `httpx 0.28.1`,
`pytest 8.4.1`, `pytest-asyncio 1.1.0`. Node v22.17.0 / npm 10.9.2. Docker CLI 27.1.1 present but
the Docker Desktop daemon is **not running**. Git 2.46.0 with credential helper `manager`.
`gh` CLI is **not installed**.

---

## 2. Reusable parts (keep or port)

| Part | Verdict | Notes |
|---|---|---|
| `selector_func` workflow logic | **PORT** | The intended flow (research -> validate -> plan -> validate -> write) is correct product behaviour. It becomes LangGraph conditional edges. |
| `ValidatorAgent` (code-based, not LLM) | **PORT** | Validating structured output with Pydantic instead of asking an LLM is the right call and is a product differentiator. |
| `utils/validation.py` schemas | **PORT + EXTEND** | Good seed for the typed data model, but far too small (see gaps). |
| Markdown-fence JSON extraction in the validator | **PORT** | Needed because models wrap JSON in fences even with `json_object` mode. |
| `validate_json_with_model` returning a tagged string (`VALIDATION_SUCCESS/FAILURE/SKIPPED`) | **PORT, CHANGE SHAPE** | String-tag protocol is fragile; it must become a structured object (`ValidationOutcome`). |
| `web_search` tool returning `{ok, answer, sources}` | **PORT** | The shape is reasonable; the implementation must move behind the provider/fallback architecture of Phase 3. |
| Termination-condition helper | **PORT** | Becomes part of the supervisor's termination policy. |
| Persian prompts and TOMAN budgeting knowledge | **PORT** | Domain content is valuable; hard-coding "Iran only" is not (see below). |

---

## 3. Bugs (confirmed by reading the code)

| # | Severity | Location | Bug |
|---|---|---|---|
| B1 | **High** | `tests/test_tools.py:19-20` | `assert "Error" not in result` on a dict, then `assert "Summary Answer" in result`. Neither assertion can pass: the tool returns a dict without that key. **The test suite is red.** |
| B2 | **High** | `tests/agent_test.py:20-22` | Asserts the researcher description is `"Conducts destination research for Iran..."`, but `agents/researcher.py:42` defines `"Uses web search to find up-to-date travel info for Iran..."`. **Always fails.** |
| B3 | **High** | `config/settings.py:56-60` | Raises `RuntimeError` at **import time** when `GOOGLE_API_KEY` is missing. Any tool, test or CLI run without a Gemini key crashes on import, including tests that do not need a model. |
| B4 | **High** | `models/GoogleModel.py:23-29` | `extra_create_kwargs` is defined at module level but **never attached to the client or the agents**; each agent re-implements its own `extra_body`. Dead code plus duplication. |
| B5 | **Medium** | `models/GoogleModel.py:9` | `json_output=True` **and** `structured_output=True` are both declared. This makes AutoGen believe any Pydantic schema can be enforced natively, which the Gemini OpenAI-compat endpoint cannot guarantee. |
| B6 | **Medium** | `teams/travel_team.py:47-48` | `content = (getattr(msg, "content", "") or "")` followed by `content = last.content or ""`. If `content` is a **list** of content parts (valid in AutoGen), `in` checks in `_validation_state` silently misbehave. No `isinstance(content, str)` guard. |
| B7 | **Medium** | `teams/travel_team.py:91-103` | Routing after validation depends on the validator's message containing the substring `"ResearchReport"` / `"ItineraryPlan"`. This couples control flow to English prose and breaks if the wording changes. The validator should return a typed outcome. |
| B8 | **Medium** | `teams/travel_team.py:134` | `allow_repeated_speaker=True` with no loop counter: a validator that keeps returning failure loops until `max_turns` is exhausted, burning tokens with no bounded repair. |
| B9 | **Medium** | `utils/utils.py:17-40` | `save_state` / `load_state` are never called anywhere in the codebase. The "persisted state" capability is dead code. |
| B10 | **Low** | `utils/validation.py:19,35` | `currency: Literal["TOMAN"]` hard-codes Iranian currency into the **data model**, making international trips impossible without a schema fork. |
| B11 | **Low** | `main.py:19` | The task string is hard-coded; there is no CLI argument parsing, no `--demo` mode, no input validation. |
| B12 | **Low** | `agents/writer.py:21-24` | `temperature: max(0.5, app_cfg.TEMPERATURE)` silently overrides a lower configured temperature. Intentional or not, it is undocumented and unconfigurable. |

---

## 4. Technical debt

| # | Area | Debt |
|---|---|---|
| D1 | Layout | Flat top-level packages (`agents/`, `tools/`, `utils/`, `models/`) with **no `src/` layout, no `py.typed`, no packaging metadata**. `tests/conftest.py` patches `sys.path` manually. |
| D2 | Dependencies | `requirements.txt` has **no version pins at all** and no lockfile. Non-reproducible builds. |
| D3 | Quality gates | **No linter, no type checker, no coverage config.** `pytest.ini` sets `asyncio_mode = auto` but the file has no `testpaths` or `pythonpath`. |
| D4 | Configuration | Three separate dataclasses, no single source of truth, no validation, no `.env.example`, secrets and behaviour split across ad-hoc variables. |
| D5 | Provider coupling | `agents/researcher.py:2` and `agents/planner.py:2` import `google_cfg` directly. The LLM layer is **not** provider-agnostic; swapping providers requires editing three agent files. |
| D6 | Observability | `logging.basicConfig` in `main.py` only. No request IDs, no structured logs, no token/cost accounting, no tracing. |
| D7 | Error handling | `main.py` catches five `openai` exception types but the team builder and agents have no error handling; a single tool failure aborts the run. |
| D8 | Testing | 3 test files, no fixtures directory, no mocks, no integration or e2e tests, no evaluation harness. `test_tools.py` hits the **live** Tavily API inside the unit suite. |
| D9 | Data layer | None. No database, no cache, no migrations, no repository layer. |
| D10 | API layer | None. No HTTP API, no streaming, no auth. |
| D11 | Frontend | None. No web client at all. |
| D12 | Docs | No README, no `docs/`, no architecture or data-source documentation. |
| D13 | Environment | The committed `.venv` is **broken**: `.venv\Scripts\python.exe` resolves to `F:\AgenticAI\AutoGen\Projects\Travel Planner\.venv\...`, a path that does not exist. Every `.\.venv\Scripts\...` invocation fails with "Unable to create process". |
| D14 | Secrets hygiene | `.env` is correctly git-ignored (good), but real Google and Tavily keys are present in the working copy. They must never be copied into docs, examples or commits. |

---

## 5. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **Iran connectivity / sanctions** | Western APIs and some model endpoints may be unreachable or restricted. | Core app must run on self-hostable, open components; model gateway is configurable (apmix / OpenAI-compatible / Ollama / mock). Documented for legal review. |
| R2 | **No official hotel/transport APIs** | The core commercial value depends on data we cannot access via a paid API. | Phase 3 scraping-first + curated datasets + estimators, all behind `Protocol` interfaces so official APIs replace scrapers by changing one env line. |
| R3 | **Legal/ToS exposure from scraping** | Aggressive scraping could violate ToS or robots.txt. | Shared `ScraperClient` enforces robots.txt, rate limits and caching; every source is registered in `SOURCES.md` with a risk level; high-risk sources are escalated to the owner, not scraped. |
| R4 | **Visa/entry-rule liability** | Stating entry rules wrongly can harm users. | These facts are always `status: estimated/inferred` with a mandatory "verify with official source" warning. Never `confirmed` without a dated official source. |
| R5 | **Model fragility** | A free-tier model may return malformed JSON, loop, or emit parallel tool calls (verified: this gateway does). | Pydantic validation at every boundary, bounded critic/replanner loops, deterministic fallbacks, `mock` provider for offline tests. |
| R6 | **Hallucinated prices** | Invented prices are a commercial and legal hazard. | Prices only ever come from a provider with `source`, `retrieved_at`, `status` and `confidence`. When unavailable the result is `status: unavailable`, never invented. |
| R7 | **Scope explosion** | The master prompt describes a multi-year product. | Ten gated phases, one branch each, no phase starts before the previous gate is green. |
| R8 | **Environment limits** | No Docker daemon, no `gh` CLI, no Postgres/Redis locally. | SQLite + in-process fallbacks so tests run anywhere; Docker-dependent items are explicitly reported as *implemented, not verified*. |
| R9 | **Git push authentication** | GCM has no confirmed token; a push could fail mid-phase. | Tested at the very start of Phase 0 (the first gate). If it fails we stop and ask for a PAT. |
| R10 | **Prompt injection from scraped pages** | Untrusted web content could hijack an agent. | Sanitize and strip scripts, filter injection patterns before any LLM call, SSRF-safe fetcher with allow/deny lists, no tool execution driven by page content. |

---

## 6. Verdict

The prototype is a **useful spike, not a foundation**. Its three genuine ideas - deterministic
selector routing, code-based validation, and explicit JSON contracts - are worth porting. Everything
else (provider coupling, Iran-only hard-coding, absence of persistence/API/UI/providers) must be
rebuilt. The decision to move orchestration from AutoGen to **LangGraph** (ADR-002) follows directly
from this audit: the product needs typed resumable state and a first-class trace, not a chat loop.
