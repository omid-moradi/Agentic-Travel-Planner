"""Live Mode: today's plan and one-tap re-plan reasons.

During the trip the user needs two things quickly, possibly offline:
**what is next** (today's activities, where I am in them) and **re-plan
today** for a concrete reason (rain, a closed venue, running late, tired,
budget change). Both are computed from the stored itinerary - deterministic,
no LLM.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Literal

from travel_planner.schemas import Itinerary

#: The concrete re-plan reasons surfaced as one-tap buttons in the UI.
Reason = Literal["rain", "closed_venue", "running_late", "tired", "budget_changed"]

REASON_LABELS: dict[str, str] = {
    "rain": "Rain today - prefer indoor activities",
    "closed_venue": "A venue is closed - swap it",
    "running_late": "Running late - compress today",
    "tired": "Tired - a lighter day",
    "budget_changed": "Budget changed - cheaper day",
}


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
