"""Live Mode: today's plan and one-tap re-plan reasons.

During the trip the user needs two things quickly, possibly offline:
**what is next** (today's activities, where I am in them) and **re-plan
today** for a concrete reason (rain, a closed venue, running late, tired,
budget change). Both are computed from the stored itinerary - deterministic,
no LLM.

``apply_reason`` is the reason-aware, day-scoped transform: it patches only
today's day plan with a deterministic change for the chosen reason. Other
days are never touched by a re-plan.
"""

from __future__ import annotations

import math
from datetime import date as date_type
from typing import TYPE_CHECKING, Literal

from travel_planner.data.fixtures.iran import estimated_price
from travel_planner.graph.nodes.planner import (
    _DAY_START_MINUTES,
    _HOTEL_NIGHT_COST,
    _walk_segment,
)
from travel_planner.schemas import Itinerary, TransportMode

if TYPE_CHECKING:
    from travel_planner.schemas import DayActivity, DayPlan

#: The concrete re-plan reasons surfaced as one-tap buttons in the UI.
Reason = Literal["rain", "closed_venue", "running_late", "tired", "budget_changed"]

REASON_LABELS: dict[str, str] = {
    "rain": "Rain today - swap walking legs for taxis",
    "closed_venue": "A venue is closed - drop it and continue",
    "running_late": "Running late - compress today",
    "tired": "Tired - a lighter day",
    "budget_changed": "Budget changed - cheaper day",
}

#: How much later the day starts when the traveller is running late.
_LATE_SHIFT_MINUTES = 120
#: Maximum activities kept for a "tired" (lighter) day.
_TIRED_MAX_ACTIVITIES = 3
#: Price levels kept when the budget changed (1-2 = free/cheap).
_CHEAP_LEVELS = {1, 2}


def _duration_minutes(start: str, end: str) -> int:
    sh, sm = (int(part) for part in start.split(":"))
    eh, em = (int(part) for part in end.split(":"))
    return max(15, (eh * 60 + em) - (sh * 60 + sm))


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _rebuild(
    day: DayPlan, activities: list[DayActivity], start_minutes: int = _DAY_START_MINUTES
) -> DayPlan:
    """Reschedule the kept activities, re-link transport, recompute the budget."""
    cursor = start_minutes
    rebuilt: list[DayActivity] = []
    for activity in activities:
        duration = _duration_minutes(activity.start_time, activity.end_time)
        rebuilt.append(
            activity.model_copy(
                update={
                    "start_time": _hhmm(cursor),
                    "end_time": _hhmm(cursor + duration),
                    "transport_to_next": None,
                }
            )
        )
        cursor += duration

    # Re-link walking/taxi legs between the kept activities.
    for i in range(len(rebuilt) - 1):
        here = rebuilt[i].place
        there = rebuilt[i + 1].place
        if here.coordinates and there.coordinates:
            rebuilt[i].transport_to_next = _walk_segment(here, there)

    entries = sum(a.cost.amount for a in rebuilt if a.cost)
    transport = sum(
        a.transport_to_next.cost.amount
        for a in rebuilt
        if a.transport_to_next and a.transport_to_next.cost
    )
    hotel_cost = 0.0
    if day.accommodation is not None:
        level = day.accommodation.price_level or 2
        hotel_cost = _HOTEL_NIGHT_COST[level]

    return day.model_copy(
        update={
            "activities": rebuilt,
            "daily_budget": estimated_price(
                entries + transport + hotel_cost,
                "entries + local transport + one hotel night",
            ),
        }
    )


def today_plan(
    itinerary: Itinerary, today: date_type | None = None
) -> dict[str, object]:
    """The plan for today with next-stop navigation hints.

    ``next_stop`` is the first activity that has not ended yet, based on the
    caller-supplied clock so tests are deterministic.
    """
    current = today or date_type.today()
    day = next((d for d in itinerary.days if d.date == current), None)

    if day is None:
        # Not on a trip day: show the first upcoming day (or none).
        upcoming = [d for d in itinerary.days if d.date >= current]
        day = upcoming[0] if upcoming else (itinerary.days[0] if itinerary.days else None)
        is_today = False
    else:
        is_today = True

    if day is None:
        return {"is_today": False, "day": None, "next_stop": None}

    return {
        "is_today": is_today,
        "day": {
            "day_number": day.day_number,
            "date": day.date.isoformat(),
            "city": day.city,
            "activities": [
                {
                    "name": a.place.name,
                    "start_time": a.start_time,
                    "end_time": a.end_time,
                    "status": a.place.status.value,
                }
                for a in day.activities
            ],
        },
        "next_stop": (
            day.activities[0].place.name if day.activities else None
        ),
    }


def replan_reasons() -> list[dict[str, str]]:
    """The one-tap re-plan buttons with their user-facing labels."""
    return [
        {"reason": reason, "label": label} for reason, label in REASON_LABELS.items()
    ]


def apply_reason(day: DayPlan, reason: Reason) -> DayPlan:
    """The deterministic, reason-aware patch for one day plan.

    Every transform keeps the day structurally valid (ordered times,
    linked legs, a recomputed budget). Venue attributes like indoor/outdoor
    arrive with provider-backed places; until then the transforms use only
    data every place already carries (price level, coordinates).
    """
    activities = list(day.activities)

    if reason == "tired":
        # A lighter day: keep the first activities of the route only.
        return _rebuild(day, activities[:_TIRED_MAX_ACTIVITIES])

    if reason == "closed_venue":
        # The closed venue is dropped; the day continues from the next one.
        kept = activities[1:] if len(activities) > 1 else activities
        return _rebuild(day, kept)

    if reason == "running_late":
        # Compress today: the same route, but the day starts two hours later.
        return _rebuild(day, activities, _DAY_START_MINUTES + _LATE_SHIFT_MINUTES)

    if reason == "rain":
        # No walking in the rain: every walk leg becomes a taxi estimate.
        rain_day = _rebuild(day, activities)
        for activity in rain_day.activities:
            leg = activity.transport_to_next
            if leg is not None and leg.mode is TransportMode.WALK:
                activity.transport_to_next = leg.model_copy(
                    update={"mode": TransportMode.TAXI}
                )
        return rain_day

    if reason == "budget_changed":
        # Cheaper day: keep only free/cheap venues, or the single cheapest.
        kept = [a for a in activities if (a.place.price_level or 1) in _CHEAP_LEVELS]
        if not kept:
            kept = [min(activities, key=lambda a: a.place.price_level or 1)]
        return _rebuild(day, kept)

    # ``reason`` is a Literal validated by the caller (the router rejects
    # unknown reasons with 400 before this function is reached).


def merge_patched_today(
    old: Itinerary, fresh: Itinerary, today: date_type, reason: Reason
) -> Itinerary:
    """The new itinerary version: the fresh plan with only today patched.

    Days other than today keep the day the traveller already has, so a
    re-plan never silently rewrites the rest of the trip. The total is the
    recomputed sum of the daily budgets.
    """
    patched_days: list[DayPlan] = []
    for fresh_day in fresh.days:
        if fresh_day.date == today:
            patched_days.append(apply_reason(fresh_day, reason))
            continue
        previous = next((d for d in old.days if d.date == fresh_day.date), fresh_day)
        patched_days.append(previous)

    total = sum(d.daily_budget.amount for d in patched_days if d.daily_budget)
    if old.total_cost is not None:
        total_cost = old.total_cost.model_copy(update={"amount": math.floor(total)})
    else:
        from travel_planner.config.regions import Currency
        from travel_planner.schemas import DataStatus, PriceEstimate

        total_cost = PriceEstimate(
            amount=math.floor(total),
            currency=Currency.TOMAN,
            status=DataStatus.ESTIMATED,
            note="sum of estimated daily budgets",
        )
    return Itinerary(days=patched_days, total_cost=total_cost)
