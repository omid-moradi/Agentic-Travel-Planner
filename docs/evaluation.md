# Evaluation

The harness lives in `evaluation/` and is a **phase 8 gate deliverable**: the
committed report (with real numbers) is in `evaluation/reports/`.

## Running it

```bash
set LLM_PROVIDER=mock        # offline, reproducible (ADR-009)
set PYTHONPATH=src;.
python evaluation/runner.py
```

Writes `evaluation/reports/evaluation-report.json` and `.md`.

## Latest result (real run, committed)

- **25/25 scenarios passed (100%)**
- Latency: min 56.7 ms, mean 70.5 ms, max 112.4 ms
- Tokens: 0 - the offline graph makes no LLM calls (a live-gateway run
  would record real counts; that run is **not** reported here)

## Scenario spread (the master prompt's demanded categories)

| Category | Scenarios | Examples |
|---|---|---|
| iran_domestic | 6 | the Tehran->Shiraz golden path, a winter week, Nowruz peak, a group of 8 |
| multi_city | 3 | 5 nights split, one night per city, an uneven split |
| budget | 3 | an impossible 100-Toman budget (must warn), a tight budget, a generous one (must not) |
| incomplete | 5 | unknown city (safe fallback), no cities, no duration, a past date, a far-future date |
| international | 3 | region profile switch, English output, a USD budget |
| live_mode | 2 | re-plan reasons accepted and traced |
| edge_case | 3 | a 30-night trip, 50 travelers, a minimal one-night trip |

## Per-scenario metrics

plan produced, validity, day-count adherence, city coverage, the 8h workload
cap, budget total consistency, budget-warning behaviour, safe fallback and
latency. A scenario crash counts as a FAIL with the exception recorded - the
runner never crashes on a scenario's behalf.
