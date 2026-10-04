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
| CI on GitHub Actions | push to `main` | **verified**: run #4 (37230936920, commit `e2f3fed`) — both jobs green: python (ruff, mypy strict, offline suite, evaluation gate, pip-audit) and web (lint, build, Playwright golden path with the API booted by Playwright on Linux) |

## Implemented but NOT verified

None — the last item (CI execution) was verified above. Everything left
(Stripe/Zarinpal live calls, an OTLP collector, a live-gateway evaluation
run, real-site scraping) is gated on credentials or owner approval, not on
the codebase; see FINAL-REPORT.md section 4.

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

## Post-close hardening (2026-10-04, "fix the remaining problems")

The owner asked for the remaining fixable problems to be fixed. Four landed,
all gates re-verified (ruff clean, mypy strict clean, **225 offline tests**,
evaluation 25/25, web lint+build clean, **Playwright 2/2**):

1. **Reason-aware, day-scoped `replan-today`** — tired trims today to a lighter
   day, rain swaps walking legs for taxi estimates, closed_venue drops the
   venue, running_late shifts the start by two hours, budget_changed keeps
   only free/cheap venues. Only today's day changes; every other day keeps
   the traveller's plan. Response gained `day_patched`; the trace records it.
   (Unit + integration tests; the old "re-runs the whole plan" limitation is
   gone.)
2. **Venue rotation within a city** — the route anchor rotates per consecutive
   day so multi-day stays no longer repeat the identical optimized day.
3. **Latent workload bug fixed** — the planner's internal 8h projection
   under-counted travel minutes relative to the validator's metric; found by
   the rotation change (evaluation dropped to 22/25, which is exactly what the
   gate is for). The projection now matches `estimate_daily_workload_hours`;
   back to 25/25.
4. **Dedicated `user_credentials` table** — password hashes moved out of the
   display-safe `preferences` JSON; phase 6 legacy hashes are verified
   read-only and lazily migrated on first login. (Unit tests for both paths.)
5. **Service-worker offline e2e** — Playwright `setOffline(true)` + reload
   after SW install; the landing page renders from the SW cache. The
   "implemented, not verified" PWA item is now verified.

Still gated on credentials or owner decisions (not code): Stripe/Zarinpal
live onboarding, an OTLP collector, a live-LLM evaluation run, real-site
scraping approval.

## Fixes found by actually running CI

- The Playwright webServer command was Windows-only
  (`.venv\Scripts\python.exe`); it is now `${API_PYTHON ?? "python"}
  -m uvicorn` and the web job installs Python 3.13 + `.[api]` first.
- On a fresh checkout `.pytest_tmp` does not exist, the e2e `DATABASE_URL`
  pointed into it, and the API exited at startup — the webServer command
  now creates the directory before uvicorn boots (verified by deleting
  `.pytest_tmp` locally and passing the golden path).

## Final state of the project

10/10 phases complete on the `phase/N -> merge to main` discipline; every
phase report is in the repository with its honest verified/unverified split,
and the cross-phase summary lives in `FINAL-REPORT.md`.
