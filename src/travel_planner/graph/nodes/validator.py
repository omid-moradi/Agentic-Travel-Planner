"""The validator node - structural and semantic checks, all code, no LLM (ADR-008).

Checks (each produces a ``ValidationIssue`` with a severity):

* day numbering is sequential and dates are consecutive
* no duplicate POI within the same day
* every activity has valid HH:MM times and end > start
* the daily workload stays under the cap
* the total cost equals the sum of the daily budgets
* the requested budget is respected (warning only - the user can raise it)
"""

from __future__ import annotations

from datetime import timedelta
from itertools import pairwise

from travel_planner.optimizer.route import estimate_daily_workload_hours
from travel_planner.schemas import TravelState, ValidationIssue

_MAX_DAY_HOURS = 8.0


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def validate_itinerary(state: TravelState) -> dict[str, object]:
    """Validate the planned itinerary and record structured issues."""
    issues: list[ValidationIssue] = []
    itinerary = state.itinerary

    if itinerary is None or not itinerary.days:
        issues.append(
            ValidationIssue(
                severity="error",
                category="structure",
                description="The itinerary is empty; nothing to validate.",
            )
        )
        return {
            "validation_issues": issues,
            "is_valid": False,
            "current_step": "validate",
        }

    days = itinerary.days

    # Sequential day numbers and consecutive dates.
    for i, day in enumerate(days, start=1):
        if day.day_number != i:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="sequence",
                    description=f"Day numbering broken: position {i} has day_number {day.day_number}",
                    affected_day=day.day_number,
                )
            )
    for prev, curr in pairwise(days):
        if curr.date - prev.date != timedelta(days=1):
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="dates",
                    description=(
                        f"Dates are not consecutive: {prev.date} then {curr.date}"
                    ),
                    affected_day=curr.day_number,
                )
            )

    for day in days:
        # Duplicated POIs within a day.
        names = [a.place.name for a in day.activities]
        duplicates = {n for n in names if names.count(n) > 1}
        for name in duplicates:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="duplicates",
                    description=f"'{name}' appears more than once on day {day.day_number}",
                    affected_day=day.day_number,
                    affected_activity=name,
                )
            )

        # Time sanity: end after start, in order.
        for activity in day.activities:
            if _hhmm_to_minutes(activity.end_time) <= _hhmm_to_minutes(activity.start_time):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="time",
                        description=(
                            f"'{activity.place.name}' on day {day.day_number}: "
                            "end time is not after the start time"
                        ),
                        affected_day=day.day_number,
                        affected_activity=activity.place.name,
                    )
                )

        # Workload cap.
        hours = estimate_daily_workload_hours(day.activities)
        if hours > _MAX_DAY_HOURS:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="workload",
                    description=(
                        f"Day {day.day_number} workload is {hours:.1f}h, over the {_MAX_DAY_HOURS}h cap"
                    ),
                    affected_day=day.day_number,
                )
            )

        # A day with no activities at all.
        if not day.activities:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    category="workload",
                    description=f"Day {day.day_number} has no activities",
                    affected_day=day.day_number,
                )
            )

    # Budget totals.
    daily_sum = sum(d.daily_budget.amount for d in days if d.daily_budget)
    if itinerary.total_cost is not None and abs(itinerary.total_cost.amount - daily_sum) > 1:
        issues.append(
            ValidationIssue(
                severity="error",
                category="budget",
                description=(
                    f"Total cost {itinerary.total_cost.amount:,.0f} does not match "
                    f"the sum of daily budgets {daily_sum:,.0f}"
                ),
            )
        )

    requested = state.request.budget_total
    if (
        requested is not None
        and itinerary.total_cost is not None
        and itinerary.total_cost.amount > requested
    ):
        issues.append(
            ValidationIssue(
                severity="warning",
                category="budget",
                description=(
                    f"Estimated total {itinerary.total_cost.amount:,.0f} exceeds the "
                    f"requested budget {requested:,.0f}"
                ),
            )
        )

    errors = [i for i in issues if i.severity == "error"]
    return {
        "validation_issues": issues,
        "is_valid": not errors,
        "current_step": "validate",
    }
