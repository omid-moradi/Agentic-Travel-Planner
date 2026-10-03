# STATUS - Phase 5 (Web application)

Date: 2026-10-03
Branch: `phase/5-web`
Gate: Playwright golden path - create trip -> edit -> share. **Passed.**

---

## Done

- [x] `web/` - Next.js 16 (App Router) + TypeScript + Tailwind CSS 4.
- [x] i18n `fa`/`en` with **full RTL**: a dependency-free dictionary, a
      LangProvider context, `dir` switching, **Persian digits** in the fa
      locale, and a language toggle in the header.
- [x] Typed API client (`web/src/lib/api.ts`) against the phase 4 FastAPI,
      with the error envelope surfaced as `ApiClientError`.
- [x] Screens:
      - `/` Landing: hero, the four product differentiators, CTAs.
      - `/new` Chat-style request: textarea + nights + travelers, planning
        indicator, error state.
      - `/trips` History: status-coloured cards (done/failed/planning).
      - `/trips/{id}` Trip detail: day tabs, timeline with times and
        walk/taxi legs, per-day and total budgets in Toman, provenance
        badges on every activity, warnings, the agent trace panel, re-plan
        and share actions.
      - `/share/{token}` Public read-only page reusing the same itinerary
        view - no edit actions exist there by design.
- [x] Playwright config boots the **whole stack itself** (uvicorn API with
      `LLM_PROVIDER=mock` + `npm run start`) so the gate is one command.
- [x] CORS added to the FastAPI app (localhost origins, tightened via env
      in production) - found by the golden path, fixed in the API.

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Web lint | `npm run lint` (web) | **clean** (0 errors, 0 warnings) |
| Web build | `npm run build` (web) | **6 routes compiled, TypeScript clean** |
| **Gate: golden path** | `npx playwright test` | **1 passed** - create trip -> re-plan -> share, against the real API and the real graph, offline |
| Python lint | `ruff check src tests scripts` | **All checks passed** |
| Python types | `mypy` (strict, 52 files) | **no issues** |
| Python tests | `pytest -q -m "not live"` | **164 passed** |
| API e2e still green | `pytest tests/integration/test_api.py` | **15 passed** |

The golden path drives a real browser: landing renders in Persian RTL ->
request form submits -> the URL moves to `/trips/{uuid}` -> the total cost
appears in Toman -> activities carry provenance badges -> the trace panel
lists steps -> re-plan produces a new version -> the share button copies the
public link -> the history page lists the trip.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| Leaflet map on the itinerary | coordinates exist in the payload but the map widget is deferred to keep this phase's gate green; the data contract is ready | phase 5.1 with OSM tiles |
| Live planning progress (SSE) | the offline graph finishes in under a second, so there is nothing to stream yet | when live providers make planning slow (phase 6+) |
| PWA Live Mode / offline cache | needs the service worker + today's-plan view | phase 7 (whole-trip features) |
| Expense tracker, account/billing, admin | scheduled phases 6-7 | later phases |
| Jalali calendar display | Gregorian dates are shown now; the Jalali conversion is a formatting concern | phase 5.1 (needs jalaali-js or similar) |

## Known limitations (honest)

- "Edit" in this phase is **re-plan** (a fresh deterministic plan version).
  Conversational edits ("cheaper", "remove museums") are designed but arrive
  with the edit-patch work in a later phase - recorded in the phase 2 status.
- The language switch is client-side per session (no cookie/localStorage
  persistence yet); the default is Persian RTL.
- Dark mode comes from the OS preference via Tailwind's dark classes; no
  manual toggle yet.
- The Windows temp directory is not writable in this environment, so the API
  test fixture uses a project-local `.pytest_tmp`.

## Decisions taken

- **Dependency-free i18n**: two locales with a compile-time-known key set;
  next-intl would add weight the product does not need yet.
- **Client components for the interactive screens** - the pages talk to the
  API directly; SSR would add a proxy layer without user value at this stage.
- **Playwright boots the full stack** (uvicorn + Next) so the golden path is
  reproducible with one command and CI does not need orchestration scripts.
- **CORS fixed in the API, not proxied away** - a real browser hit the
  cross-origin request, so the API needs the middleware; an allowlist with
  localhost origins is the honest development default.

## Next - Phase 6 (Monetization)

1. Auth: email + OAuth skeleton, JWT, roles, guest trial.
2. `EntitlementService` + usage metering enforcement (plans/replans/tokens).
3. `PaymentProvider` interface; Stripe + Zarinpal adapters behind a feature
   flag, test mode only, webhooks with idempotency.
4. Affiliate link service (redirect only, click tracking, disclosure).
5. Admin dashboard: users, usage, cost per plan, funnel, provider health.
6. Gate: webhook + entitlement tests green.
