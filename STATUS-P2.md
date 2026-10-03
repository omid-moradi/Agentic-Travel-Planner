# STATUS - Phase 2 (Agentic core and optimizer)

Date: 2026-10-03
Branch: `phase/2-agents`
Gate: the CLI plans a valid Tehran -> Shiraz trip **offline**. **Passed.**

---

## Done

- [x] `travel_planner.schemas` - the full typed data model:
      `DataStatus` (confirmed/estimated/inferred/unavailable on every fact),
      `TripRequest`, `TravelState` (the LangGraph state), `Finding`, `PlaceInfo`,
      `PriceEstimate`, `OpeningHours`, `RouteSegment`, `DayActivity`, `DayPlan`,
      `Itinerary`, `ValidationIssue`, plus enums for transport/accommodation/style.
- [x] `travel_planner.data.fixtures.iran` - curated Tehran/Shiraz venues, hotels and
      restaurants with coordinates, opening hours, durations and a dated source.
- [x] `travel_planner.optimizer.route` - the deterministic engine (ADR-008, no LLM):
      haversine distance, greedy geographic clustering, nearest-neighbour ordering,
      2-opt local search, daily workload estimation and the 8h cap.
- [x] `travel_planner.graph` - the LangGraph workflow:
      - 9 parallel research nodes fan out from START (places, accommodation, restaurants,
        transport, weather, events, culture, safety, requirements),
      - a deterministic planner (day distribution across cities, route optimization,
        time scheduling from visit durations, walk-vs-taxi legs, workload capping,
        Toman budgeting with documented heuristics),
      - a code validator (sequence, consecutive dates, duplicate POIs, time sanity,
        workload cap, budget totals, requested-budget warning),
      - a bounded replan loop (`repair_count < max_repair_loops`, then best-effort),
      - a writer that renders Persian or English output with confidence labels and a
        prices-may-differ notice.
- [x] CLI `travel-planner plan` - full argument surface (cities, nights, start date,
      travelers, budget, language, region, thread id, `--demo`).
- [x] 48 new tests: schemas (25), optimizer (14), end-to-end graph (9).

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 22 files) | **Success: no issues found** |
| Offline tests | `pytest -q -m "not live"` | **107 passed** |
| Coverage | `pytest --cov` | **82% total** (planner 98%, optimizer 93%, schemas 98%) |
| **Phase gate** | `travel-planner plan --demo --nights 3 --start 2026-11-01` | **exit 0** - valid 3-day Tehran->Shiraz plan, `validation: OK` |
| Zero network | graph runs with no API key and no provider | **verified** (fixtures only) |

The gate output is a real multi-city plan: days 1-2 in Tehran (Milad Tower, National
Museum, Golestan Palace, Grand Bazaar in optimizer order with travel times between them),
day 3 in Shiraz (Vakil Bazaar, Pink Mosque, Eram Garden, Tomb of Hafez), per-day and
total budgets in labelled Toman, every activity carrying its provenance status.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| SQLite/Postgres checkpointing | `langgraph-checkpoint-sqlite` is not importable in this environment (the extra package did not install cleanly); the graph uses `MemorySaver` | phase 4 persistence installs and uses a durable checkpointer |
| Opening-hours enforcement in the planner | the validator checks times and workload, but the planner does not yet shift activities past a venue's closing time | phase 3, once opening hours come from real providers |
| Intercity legs inside the itinerary | the transport research node produces Tehran->Shiraz estimates, but the planner does not yet insert a travel day between cities | phase 3 (real transport data) |
| Conversational edit path | designed in the plan; the patch-and-revalidate flow is not built yet | phase 5 (chat UI) or earlier if needed |

## Known limitations (honest)

- **Days within one city are identical** in phase 2: the fixture set has 4-5 venues per
  city, so a 2-night stay in Tehran repeats the same optimized day. Real providers
  (phase 3) will supply enough venues to diversify; the planner already supports more.
- Prices are documented heuristics (entry fee by price level, taxi per-km, hotel night
  by price level) - labelled `estimated` everywhere, never presented as confirmed.
- The critic/replanner loop is bounded and observable, but since the planner is
  deterministic a re-run rarely changes the outcome; its real value begins when
  validation failures can be repaired by re-running individual research nodes (phase 3+).

## Decisions taken

- Research nodes do not write `current_step` (LangGraph rejects concurrent writes to a
  LastValue channel); flow control stays on sequential nodes only.
- The writer is pure Python in this phase. LLM narrative will be layered on top of the
  validated plan later, never instead of it.
- Persian UI copy triggers RUF001 (Arabic-script lookalikes); the writer module is
  exempted in `pyproject.toml` rather than disabling the rule globally.

## Next - Phase 3 (Data providers, scraping-first)

1. `providers/` layout with `Protocol` interfaces and a `ProviderRegistry` driven by env.
2. Shared `ScraperClient` (robots.txt, rate limit, cache, circuit breaker, sanitization).
3. Curated dataset + estimator providers for hotels, transport and ride fares.
4. Open-Meteo weather, Nominatim geocoding, OSRM routing.
5. Parser contract tests with HTML fixtures; `docs/data-sources.md`.
6. Gate: parser contract tests green + documented live smoke tests.
