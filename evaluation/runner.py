"""The evaluation runner: executes every scenario against the real graph.

Offline and reproducible: the LLM is forced to ``mock`` and the graph runs on
the curated fixtures, so a re-run produces identical results (ADR-009).
Metrics per scenario: validity, day-count adherence, city coverage, workload
feasibility, budget consistency, budget-warning behaviour, safe fallback and
latency. The report writes JSON and Markdown.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.scenarios import SCENARIOS, Scenario
from travel_planner.config.settings import Language, Region
from travel_planner.graph import run_plan
from travel_planner.optimizer.route import estimate_daily_workload_hours
from travel_planner.schemas import TripRequest

REPORTS_DIR = Path(__file__).parent / "reports"


def _trip_request(scenario: Scenario) -> TripRequest:
    payload = scenario.request
    start = payload.get("start_date")
    return TripRequest(
        raw_input=str(payload.get("request", "")),
        region=Region(str(payload.get("region", "iran"))),
        language=Language(str(payload.get("language", "fa"))),
        destinations=list(payload.get("destinations", []) or []),  # type: ignore[arg-type]
        start_date=start,  # type: ignore[arg-type]
        duration_nights=payload.get("duration_nights", None),  # type: ignore[arg-type]
        travelers=payload.get("travelers", 1),  # type: ignore[arg-type]
        budget_total=payload.get("budget_total", None),  # type: ignore[arg-type]
    )


def _run_graph(request: TripRequest, name: str) -> Any:
    import asyncio as _asyncio

    return _asyncio.run(run_plan(request, thread_id=f"eval-{name}"))


def _evaluate_one(scenario: Scenario) -> dict[str, Any]:
    """Run one scenario and score it against its expectations."""
    start_clock = time.perf_counter()
    outcome: dict[str, Any] = {
        "name": scenario.name,
        "category": scenario.category,
        "description": scenario.description,
        "checks": {},
    }
    try:
        state = _run_graph(_trip_request(scenario), scenario.name)
        outcome["latency_ms"] = round((time.perf_counter() - start_clock) * 1000, 1)
        checks: dict[str, bool] = {}
        expectations = scenario.expectations

        itinerary = state.itinerary
        checks["plan_produced"] = itinerary is not None
        if itinerary is not None:
            day_count = len(itinerary.days)
            checks["valid"] = state.is_valid == expectations.valid
            checks["day_count"] = expectations.min_days <= day_count <= expectations.max_days
            cities = {day.city.lower() for day in itinerary.days}
            checks["cities_covered"] = all(city in cities for city in expectations.cities)
            checks["workload_capped"] = all(
                estimate_daily_workload_hours(day.activities) <= 8.0
                for day in itinerary.days
            )
            daily_sum = sum(d.daily_budget.amount for d in itinerary.days if d.daily_budget)
            total = itinerary.total_cost.amount if itinerary.total_cost else None
            checks["budget_consistent"] = total is None or abs(total - daily_sum) <= 1

        budget_warnings = [
            i for i in state.validation_issues
            if i.severity == "warning" and i.category == "budget"
        ]
        checks["budget_warning"] = (
            bool(budget_warnings) if expectations.expect_budget_warning else True
        )
        checks["safe_fallback"] = (
            True if not expectations.expect_safe_fallback else bool(state.itinerary)
        )

        outcome["checks"] = checks
        outcome["passed"] = all(checks.values())
        outcome["repair_loops"] = state.repair_count
    except Exception as exc:  # a scenario crash is a result, not a runner crash
        outcome["latency_ms"] = round((time.perf_counter() - start_clock) * 1000, 1)
        outcome["error"] = f"{type(exc).__name__}: {exc}"
        outcome["passed"] = False
    return outcome


def run_evaluation() -> dict[str, Any]:
    """Run every scenario and build the full report."""
    results = [_evaluate_one(scenario) for scenario in SCENARIOS]
    passed = sum(1 for r in results if r.get("passed"))
    latencies = [r.get("latency_ms", 0) for r in results]
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "offline (mock LLM, curated fixtures)",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results) * 100, 1) if results else 0.0,
        "latency_ms": {
            "min": min(latencies) if latencies else 0,
            "mean": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "max": max(latencies) if latencies else 0,
        },
        "tokens": {"total": 0, "note": "the offline graph makes no LLM calls"},
        "by_category": {},
        "results": results,
    }
    for result in results:
        category = result["category"]
        bucket = report["by_category"].setdefault(category, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if result.get("passed"):
            bucket["passed"] += 1
    return report


def write_reports(report: dict[str, Any], directory: Path | None = None) -> tuple[Path, Path]:
    """Persist the report as JSON and Markdown; returns both paths."""
    target = directory or REPORTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "evaluation-report.json"
    md_path = target / "evaluation-report.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Evaluation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: {report['mode']}",
        "",
        f"**{report['passed']}/{report['total']} scenarios passed ({report['pass_rate']}%)**",
        "",
        f"Latency (ms): min {report['latency_ms']['min']}, "
        f"mean {report['latency_ms']['mean']}, max {report['latency_ms']['max']}",
        "",
        "| Category | Passed | Total |",
        "|---|---|---|",
    ]
    for category, bucket in sorted(report["by_category"].items()):
        lines.append(f"| {category} | {bucket['passed']} | {bucket['total']} |")
    lines += ["", "| Scenario | Category | Result | Latency (ms) |", "|---|---|---|---|"]
    for result in report["results"]:
        verdict = "PASS" if result.get("passed") else "FAIL"
        lines.append(
            f"| {result['name']} | {result['category']} | {verdict} "
            f"| {result.get('latency_ms', '-')} |"
        )
        if result.get("error"):
            lines.append(f"  - error: `{result['error']}`")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    final = run_evaluation()
    json_file, md_file = write_reports(final)
    print(f"{final['passed']}/{final['total']} passed ({final['pass_rate']}%)")
    print(f"JSON: {json_file}")
    print(f"Markdown: {md_file}")

