# STATUS - Phase 7 (Whole-trip features)

Date: 2026-10-03
Branch: `phase/7-whole-trip`
Gate: export tests green; Live Mode replan covered by unit tests. **Passed.**

---

## Done

- [x] **Checklists** (`services/checklists.py`): a deterministic packing list
      (region- and season-aware, Iran-specific items: modest dress, headscarf,
      cash for ride apps) where every item carries its reason; a document
      checklist (domestic: national ID + insurance; international: passport
      with the 6-month validity rule, visa, insurance, tickets) whose payload
      always carries the verify-with-official-source warning.
- [x] **Entry requirements** (`services/entry_requirements.py`): advisory only
      (ADR-009). International items are labelled ``inferred`` and every
      response carries the mandatory warning; the domestic national-ID item
      is the one ``confirmed`` rule.
- [x] **Expense tracker** (`services/expenses.py`, new ``expenses`` table):
      record expenses in TOMAN/IRR/USD/EUR/GBP/TRY/AED, converted at insert
      time via a documented static rate table behind the same interface a
      live currency provider replaces in phase 8; per-category burn-down
      against the itinerary's estimated total (spent/budget/remaining).
- [x] **Exports** (`services/exports.py`):
      - **ICS**: RFC 5545 calendar, one all-day VEVENT per trip day, CRLF
        line endings, DTSTART;VALUE=DATE, escaped summaries.
      - **PDF**: a minimal, hand-rolled, dependency-free single-page writer -
        correct xref offsets, %%EOF, Helvetica - so the export adds zero new
        dependencies and opens in every reader.
- [x] **Live Mode** (`services/live_mode.py`): ``today`` resolves the plan for
      the caller's date (or the next trip day) with next-stop navigation
      hints; ``replan-today`` runs the deterministic planner for a concrete
      reason (rain / closed venue / running late / tired / budget changed)
      and records the reason on the agent trace so every edit is auditable.
- [x] **PWA** (web): ``manifest.json`` (RTL, fa, standalone, theme colour),
      ``icon.svg``, and a service worker (cache-first for GETs, network
      fallback to cache) registered by a client component - the itinerary
      keeps working offline.
- [x] Endpoints: ``GET /trips/{id}/checklist``, ``GET .../entry-requirements``,
      ``POST|GET .../expenses``, ``GET .../export.ics``, ``GET .../export.pdf``,
      ``GET .../today``, ``POST .../replan-today``.

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 66 files) | **Success: no issues found** |
| **Gate: whole-trip tests** | `pytest tests/integration/test_whole_trip.py` | **13 passed** |
| Full offline suite | `pytest -m "not live"` | **192 passed** |
| Web lint + build | `npm run lint` / `npm run build` | **clean / 7 routes** |
| Phase 5 golden path | `npx playwright test` | **1 passed** |

What the gate tests prove:

- the ICS export is real RFC 5545 (BEGIN/END:VCALENDAR, 3 VEVENTs for 3 days,
  CRLF, all-day date values, city in the summary) - **the export gate**;
- the PDF export is a real PDF (%PDF-1.4 header, xref table, %%EOF, one page,
  five indirect objects);
- international entry requirements are always ``inferred`` with the warning,
  never confirmed;
- the expense tracker converts USD at the documented rate and the burn-down
  arithmetic is exact (remaining = budget - spent);
- Live Mode returns all five one-tap reasons, an accepted reason lands on
  the trace, and an unknown reason is rejected with the error envelope -
  **the Live Mode gate**.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| Service worker offline behaviour | Playwright does not drive airplane mode; the SW is registered and the caching logic is standard cache-first | open a trip page, go offline in DevTools, reload |
| Reason-aware re-planning | the current re-plan re-runs the deterministic planner and records the reason; swapping indoor venues on rain needs venue attributes the fixture data does not carry | phase 8+ with richer place data |
| Live currency conversion | the static table is documented and labelled estimated; the exchangerate provider is not yet wired into expenses | phase 8 |
| Persian text in the PDF | the hand-rolled writer emits latin-1; Persian shaping/embedding needs the designed export | the ICS export serves fa users (their calendar app shapes correctly) |

## Known limitations (honest)

- The packing list is heuristic and English-only in this phase; the fa/en
  dictionary grows when the checklist screens land in the web UI.
- ``replan-today`` currently re-runs the whole plan, not just today's day.
  The endpoint contract (reason + trace) is stable; the day-scoped patch
  arrives with the provider-backed planner.
- The burn-down compares against the *estimate*, not the budget the user
  typed (the validation already warns when the estimate exceeds it).

## Decisions taken

- **PDF without a dependency**: a hand-rolled writer keeps the product
  installable anywhere and produces a valid file; the designed export can
  replace it behind the same function.
- **Expenses convert at insert time**, storing both the original and the
  normalised amount - a recorded expense must never change retroactively
  when rates move.
- **The service worker is cache-first for GETs** with a network fallback to
  cache; a stale itinerary offline is strictly better than no itinerary.

## Next - Phase 8 (Observability, evaluation and MCP)

1. Structured logs + OpenTelemetry-compatible tracing; token/cost metrics
   wired from the LLM usage the graph already records.
2. **Evaluation harness**: 20+ scenarios (Iran domestic, international,
   budget cuts, rain, incomplete requests, multi-city) with validity, budget,
   feasibility, grounding and recovery metrics; JSON + Markdown report.
3. Failure-injection suite: timeout, 429, malformed JSON, provider outage.
4. Optional MCP server exposing the same tools.
5. Gate: evaluation report with real numbers; failure injection degrades
   gracefully.

