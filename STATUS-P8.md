# STATUS - Phase 8 (Observability, evaluation and MCP)

Date: 2026-10-04
Branch: `phase/8-obs-eval-mcp`
Gate: evaluation report generated with real numbers; failure injection degrades gracefully. **Passed.**

---

## Done

- [x] **Observability** (`travel_planner.observability`):
      - ``Tracer`` emitting **OpenTelemetry-data-model spans** (trace_id, span_id,
        unix-nano timestamps, attributes, ok/error status) through the structured
        logger - an OTLP exporter can subscribe to the same records without touching
        callers. Dependency-free on purpose.
      - ``MetricsRegistry`` with thread-safe counters/gauges rendered in
        **Prometheus text format** at ``GET /api/v1/metrics``; the HTTP middleware
        counts every request with method/path/status labels.
- [x] **Evaluation harness** (`evaluation/`):
      - **25 typed scenarios** across 7 categories (iran_domestic, multi_city,
        budget, incomplete, international, live_mode, edge_case) - the master
        prompt's demanded spread, including Nowruz peak season, a 30-night trip,
        50 travelers, impossible budgets, unknown cities, past and far-future
        dates.
      - Metrics per scenario: plan produced, validity, day-count adherence, city
        coverage, the 8h workload cap, budget total consistency, budget-warning
        behaviour, safe fallback and latency.
      - Runner + JSON + Markdown report writers; reproducible (mock LLM, curated
        fixtures). CLI: ``python evaluation/runner.py``.
- [x] **Failure-injection suite** (`tests/integration/test_failure_injection.py`):
      provider timeout, empty results, a fully dead chain, malformed JSON, HTTP
      429, circuit opening/half-open, webhook replay idempotency, unknown
      live-mode reason, malformed request bodies, missing-trip subresources and
      health/metrics surviving an outage.
- [x] **MCP server** (`travel_planner.mcp.server`): a minimal, dependency-free
      JSON-RPC 2.0 stdio server speaking the MCP protocol basics (initialize,
      tools/list, tools/call) and exposing ``plan_trip`` (the real offline graph)
      and ``get_health``. **The core never imports it** - a test enforces that.

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 70 files) | **Success: no issues found** |
| Full offline suite | `pytest -m "not live"` | **211 passed** |
| **Gate: evaluation** | `python evaluation/runner.py` | **25/25 passed (100%)**, report with real latencies |
| Failure injection | `pytest tests/integration/test_failure_injection.py` | **11 passed** |
| MCP protocol | `pytest tests/unit/test_mcp.py` | **8 passed** |
| MCP live round trip | initialize -> tools/list -> tools/call over stdio | **verified**: plan_trip returned a valid 2-day plan, health OK, unknown method -> -32601 |

**Evaluation report (real numbers, committed at ``evaluation/reports/``):**

- 25/25 scenarios passed (100.0%)
- Latency: min 56.7 ms, mean 70.5 ms, max 112.4 ms (offline graph, per scenario)
- Tokens: 0 - the offline graph makes no LLM calls; a live-gateway run would
  record real token counts from the ``Usage`` accounting the LLM layer already
  implements.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| A real OTLP exporter | no collector running in this environment; spans are emitted in the OTLP data model via structured logs | run an OTel collector and point it at the log stream |
| Multi-process metrics | the registry is in-process; workers do not share counters | Redis-backed registry in production |
| Token/cost metrics per live plan | the offline graph makes no LLM calls; usage rows exist with tokens=0 | run the graph with the live gateway and read ``/api/v1/metrics`` |
| A standard MCP SDK client | the server speaks the protocol basics; full MCP feature coverage (resources, prompts, sampling) is not implemented | point an MCP client at stdio; ``initialize`` and the two tools work (verified manually) |

## Known limitations (honest)

- The evaluation runs **offline only** in this environment; the harness is built
  so a live-gateway run is a config change (``LLM_PROVIDER=apmix``), but that
  run's numbers are **not** reported here.
- The MCP server implements the protocol basics, not the full MCP surface;
  the tools it exposes mirror the API's core.
- Metrics counters reset on process restart until the Redis registry lands.

## Decisions taken

- **Dependency-free OTLP-shaped spans and Prometheus text**: both formats are
  simple; adding the otel/prom client libraries now would add weight without
  a running backend to receive it.
- **The evaluation report is a committed deliverable** (removed from
  ``.gitignore``): the phase 8 gate is a report with real numbers, and a report
  that only exists on one machine does not meet a gate.
- **The MCP server is standalone** and a test enforces that the core never
  imports it - the master prompt requires the core to work without it.

## Next - Phase 9 (DevOps and polish)

1. Dockerfiles + docker-compose (api, web, postgres, redis) with health checks.
2. CI: ruff, mypy, pytest, web lint/build, Playwright, pip-audit.
3. Pre-commit, pinned dependencies, security checks.
4. Final README + docs (architecture, agents, tools, api, deployment,
   evaluation, security, monetization, iran-mode, data-sources).
5. Final report with exact commands, env vars, known limitations and the
   go-to-market checklist.
