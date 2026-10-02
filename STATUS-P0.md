# STATUS - Phase 0 (Audit & Plan)

Date: 2026-10-02
Branch: `phase/0-audit`
Gate: docs committed and pushed to GitHub.

---

## Done

- [x] Full audit of the existing AutoGen prototype -> [`docs/audit.md`](docs/audit.md)
      (reusable parts, 12 confirmed bugs, 14 debt items, 10 risks).
- [x] Decision log with 9 ADRs -> [`docs/decisions.md`](docs/decisions.md).
- [x] Target architecture -> [`docs/architecture.md`](docs/architecture.md).
- [x] Execution plan for all 10 phases -> [`plan-mode-cline.md`](plan-mode-cline.md).
- [x] `.env.example` with every configuration variable documented and **no real secrets**.
- [x] `.env` migrated to the apmix gateway (local file only, git-ignored).
- [x] `.gitignore` hardened (secrets, caches, databases, node, evaluation output).
- [x] `README.md` rewritten with an honest work-in-progress status.

## Verified (actually executed)

| Check | Result |
|---|---|
| `GET https://api.apmix.ai/v1/models` with the new key | `200`, model `deepseek-v4-flash-free` |
| Chat completion, `model=deepseek-v4-flash-free` | `200` |
| Chat completion, `model=deepseek/deepseek-v4-flash-free` (prefixed alias) | `200` |
| Tool calling (`tools=[web_search]`) | `200`, `finish_reason=tool_calls` |
| JSON mode (`response_format={"type":"json_object"}`) | `200`, valid JSON returned |
| `pip install --dry-run langgraph` on Python 3.13.5 | would install `langgraph 1.2.12` |
| `.env` is ignored by git | confirmed via `git check-ignore -v .env` |
| `.env` absent from `git status` | confirmed |
| Runtime inventory of installed packages and versions | confirmed via `pip list` |

## Implemented but NOT verified

- Nothing in Phase 0. This phase is documentation and configuration only; no runtime code was
  written, so there is nothing unverified to report.

## Known issues found but not yet fixed (scheduled)

- `tests/test_tools.py` and `tests/agent_test.py` are **currently failing** (audit B1, B2).
  They are fixed in Phase 1.
- `config/settings.py` raises at import time without `GOOGLE_API_KEY` (audit B3). Fixed in Phase 1.
- The committed `.venv` is **broken** and points at a stale path `F:\AgenticAI\...` (audit D13).
  Rebuilt in Phase 1.
- `.env` previously contained live Google and Tavily keys. The Tavily key is retained locally;
  the unused Google key was removed. Neither is committed.

## Environment limitations (declared, not worked around)

| Item | State | Impact |
|---|---|---|
| Docker Desktop daemon | not running | Docker/compose items in Phase 9 will be reported as *implemented, not verified* unless it is started |
| `gh` CLI | not installed | Pushing uses plain `git` with the configured credential helper |
| PostgreSQL / Redis | not installed locally | Phase 4 uses the SQLite + in-process fallbacks for tests (ADR-005) |
| Project `.venv` | broken | All commands currently use the system Python 3.13.5, where the dependencies are installed |

## Decisions taken (details in `docs/decisions.md`)

- ADR-002: **LangGraph replaces AutoGen** (verified installable, 1.2.12).
- ADR-003: apmix / `deepseek-v4-flash-free` is the default gateway; the layer stays provider-agnostic.
- ADR-001: one branch per phase, merged to main only after a green gate.

## Next - Phase 1 (Core foundation and apmix migration)

1. Rebuild the virtual environment; add `pyproject.toml` with pinned dependencies.
2. Create `src/travel_planner/{config,llm}` with the provider-agnostic model factory.
3. Migrate `.env` consumption; remove the import-time `RuntimeError`.
4. Move the prototype to `legacy_prototype/`; create the new package skeleton.
5. Fix the two broken tests; add a live apmix smoke test (auto-skipped without a key).
6. Configure `ruff`, `mypy` and `pytest-cov`.
7. Gate: `ruff` OK, `mypy` OK, `pytest` OK, live call returns `200`.
