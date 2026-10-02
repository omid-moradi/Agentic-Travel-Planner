# STATUS - Phase 1 (Core foundation and apmix migration)

Date: 2026-10-02
Branch: `phase/1-core`
Gate: `ruff` OK, `mypy` OK, `pytest` OK, live call returns `200`. **All green.**

---

## Done

- [x] `.env` migrated to the apmix gateway; `LLM_PROVIDER=apmix`,
      `LLM_BASE_URL=https://api.apmix.ai/v1`,
      `LLM_MODEL=deepseek/deepseek-v4-flash-free`, key in `.env` only.
- [x] `pyproject.toml` with extras (`providers`, `search`, `api`, `dev`), `ruff`, `mypy`
      (strict), `pytest` and `pytest-cov` configuration.
- [x] `src/travel_planner/` package created with `py.typed`.
- [x] `travel_planner.errors` - one shared exception hierarchy (audit B-class bug: two
      divergent `LLMConfigurationError` classes were caught incorrectly during development).
- [x] `travel_planner.config.settings` - typed `Settings`, **no import-time validation**
      (fixes audit bug B3), secrets as `SecretStr`, `redacted()` for logging,
      `reload_settings()` for tests, comma-separated provider chains.
- [x] `travel_planner.config.regions` - `RegionProfile` for Iran / international:
      Jalali vs Gregorian, RTL vs LTR, Toman vs USD, always-labelled currencies.
- [x] `travel_planner.llm` - provider-agnostic factory:
      `apmix | openai | openai_compatible | ollama | mock`.
      - `reasoning_content` stripped at the boundary (no chain-of-thought anywhere),
      - `<think>` blocks removed,
      - parallel tool calls capped by `LLM_MAX_PARALLEL_TOOL_CALLS`,
      - markdown-fenced JSON tolerated, one repair retry before giving up,
      - token accounting via `Usage`.
- [x] `travel_planner.logging_config` - JSON/console formatters, secret and PII redaction,
      noisy third-party loggers quieted.
- [x] `travel_planner.cli` - `config` (secret-free dump) and `ping` (real completion).
- [x] `.pre-commit-config.yaml` + `scripts/check_no_secrets.py` (blocks live credentials
      from being committed).
- [x] `requirements.txt` rewritten; AutoGen deliberately removed from the product deps.
- [x] Prototype tests moved to `legacy_prototype/tests/` (they asserted on strings that no
      longer exist and could never pass - audit B1, B2). `pytest.ini` removed so
      `pyproject.toml` is the single config source.
- [x] 66 offline tests + 7 live tests + 6 CLI tests written.

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `python -m ruff check src tests scripts` | **All checks passed** |
| Types | `python -m mypy` (strict) | **Success: no issues found in 9 source files** |
| Offline tests | `python -m pytest -q` | **66 passed** |
| Coverage | `python -m pytest -q --cov` | **88%** (factory 80%, logging 92%, config 99-100%) |
| Live tests | `python -m pytest -m live` | **7 passed** against apmix |
| Live completion | `python -m travel_planner.cli ping "..."` | Persian answer returned, 264 tokens |
| Config dump | `python -m travel_planner.cli config` | valid JSON, no secret present |
| Secret scan | `python scripts/check_no_secrets.py` | passed |
| LangGraph availability | `pip install langgraph` | 1.2.12 installed and importable |

Live tests actually executed against the gateway (not mocked):

1. plain completion returns content
2. `reasoning_content` never leaks into `LLMResult.content`
3. JSON mode validates against a Pydantic schema
4. tool calling produces a `ToolCall` with parsed arguments
5. parallel tool calls are capped
6. the system message is honoured (Persian output verified)
7. an unreachable endpoint raises `LLMError` (failure injection)

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| `openai` and `ollama` providers | no credentials / no local Ollama server here | set `LLM_PROVIDER=ollama` with a running server, or point `LLM_BASE_URL` at any OpenAI-compatible endpoint |
| `pre-commit` hooks execution | `pre-commit` itself is not installed in this environment | `pip install pre-commit && pre-commit install && pre-commit run --all-files` |
| Docker / Postgres / Redis | Docker daemon is not running (declared limitation) | Phase 4 and 9 |
| Package install via `pip install -e .` | tests run through `pythonpath = ["src"]` instead | `pip install -e ".[dev]"` then run `travel-planner config` |

## Known issues found but not yet fixed (scheduled)

- The `legacy_prototype/` package still imports AutoGen and raises on import without a
  Gemini key. It is quarantined and **excluded from the test suite**; it is deleted in
  phase 4, so it is not worth fixing now.
- `travel_planner.llm.factory` coverage is 80%: the uncovered lines are the retry/repair
  path and unusual gateway responses. They are covered by the live suite, which is
  opt-in, so offline coverage does not reflect them.
- The gateway reports the served model as `space-bunny-free` while accepting the id
  `deepseek-v4-flash-free`. This is the provider's aliasing, not a bug on our side; it is
  recorded so nobody is surprised by the model name in logs.

## Environment limitations (declared, not worked around)

| Item | State | Impact |
|---|---|---|
| Docker Desktop daemon | not running | Phase 9 items reported as *implemented, not verified* |
| PostgreSQL / Redis | not installed | Phase 4 uses SQLite + in-process fallbacks (ADR-005) |
| `pre-commit` binary | not installed | hook config is committed and reviewed, but not executed here |
| Project `.venv` | still broken (audit D13) | commands use the system Python 3.13.5 |

## Decisions taken

- ADR-002 (LangGraph over AutoGen) is now **implemented**: `langgraph 1.2.12` is installed and
  importable. The graph itself lands in phase 2.
- Error classes live in `travel_planner.errors` so `config` and `llm` share one hierarchy and
  `config` stays dependency-light.
- Gemini-only request extras (`extra_body.reasoning`) are **not** carried over.

## Next - Phase 2 (Agentic core and optimizer)

1. `schemas/` - `TripRequest`, `TravelState`, `Finding`, `PlaceInfo`, `Itinerary`,
   `PriceEstimate`, with `status: confirmed | estimated | inferred | unavailable`.
2. `TravelState` as the LangGraph state, plus a SQLite checkpointer.
3. Nodes: `intent`, `supervisor`, nine parallel `research_*`, `plan`, `validate`, `critic`,
   `replanner`, `write`, and the edit path.
4. `optimizer/` - geographic clustering, nearest-neighbour + 2-opt routing, opening-hours and
   budget feasibility, daily workload caps (pure Python, no LLM - ADR-008).
5. Demo mode with fixtures, fully offline.
6. Gate: `python -m travel_planner.cli plan --demo` produces a valid Tehran -> Shiraz trip
   offline, with lint, types and tests green.
