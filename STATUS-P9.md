# STATUS - Phase 9 (DevOps and polish) — FINAL

Date: 2026-10-04
Branch: `phase/9-devops`
Gate: all previous gates still green; the final report is honest about
unverified items. **Passed.**

---

## Done

- [x] **Docker**: multi-stage `Dockerfile` (wheel build -> slim non-root
      runtime, healthcheck, demo mode by default) and `web/Dockerfile`
      (Next.js standalone; `output: "standalone"` enabled).
- [x] **docker-compose.yml**: api + web + postgres + redis with health
      checks, a JWT_SECRET guard (`:?` so a wrong env fails loudly), and a
      volume for the SQLite fallback.
- [x] **CI** (`.github/workflows/ci.yml`): python job (ruff, mypy strict,
      offline pytest, the evaluation gate, pip-audit) and a web job (lint,
      build, Playwright with the API booted by Playwright itself).
- [x] **Docs completed**: `docs/agents.md`, `docs/tools.md`, `docs/api.md`,
      `docs/deployment.md`, `docs/evaluation.md`, `docs/security.md`,
      `docs/monetization.md`, `docs/iran-mode.md` joining the existing
      `architecture.md`, `audit.md`, `decisions.md`, `data-sources.md`.
- [x] **README.md rewritten** as the product entry point: features, the four
      differentiators, quick start, Docker, testing/evaluation with real
      numbers, env vars, roadmap, legal notes.
- [x] **FINAL-REPORT.md**: what was implemented, architecture, verified vs
      implemented-but-not-ververifed tables, known limitations, exact
      commands, required env vars, and the go-to-market checklist.

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 70 files) | **no issues** |
| Offline suite | `pytest -m "not live"` | **211 passed** |
| Evaluation | `python evaluation/runner.py` | **25/25 (100%)** |
| Web | `npm run lint` + `npm run build` | **clean** |
| Golden path | `npx playwright test` | **1 passed** |
| Docker stack | `docker compose up --build` | **verified**: images built (api 277MB, web 234MB), postgres/redis healthy, api container `(healthy)`, web 200, `POST /trips` → 201 `done`, second plan → 402 quota envelope, `GET /trips` lists the trip |

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| CI workflow execution | GitHub Actions runs only on a push; the workflow mirrors the exact local gates that all passed | push to GitHub and read the run |

## Fixes found by actually verifying Docker

- `pip install` of the wheel now requests the `[api]` extra (fastapi/uvicorn
  live there, not in the core dependencies) plus `pyjwt`/`email-validator`.
- `/app/data` is created and chowned as **root** before `USER planner`
  (the app user cannot create a directory inside the root-owned `/app`).
- `.dockerignore` files added (root and `web/`) so the Windows `node_modules`
  and `.venv` never enter the build context.
- The compose `DATABASE_URL` is pinned to an absolute in-container path and
  deliberately not `${...}`-substituted: Compose reads the project `.env`,
  and the local-dev relative SQLite path broke the container
  (`unable to open database file`). `LLM_*` still flows through, so the
  real gateway key from `.env` works inside the stack.

## Final state of the project

10/10 phases complete on the `phase/N -> merge to main` discipline; every
phase report is in the repository with its honest verified/unverified split,
and the cross-phase summary lives in `FINAL-REPORT.md`.
