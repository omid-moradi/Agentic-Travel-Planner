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

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| Docker build / compose up | the Docker daemon was not running in the development environment (declared since phase 0) | `docker compose up --build` |
| CI workflow execution | GitHub Actions runs only on a push; the workflow mirrors the exact local gates that all passed | push to GitHub and read the run |

## Final state of the project

10/10 phases complete on the `phase/N -> merge to main` discipline; every
phase report is in the repository with its honest verified/unverified split,
and the cross-phase summary lives in `FINAL-REPORT.md`.
