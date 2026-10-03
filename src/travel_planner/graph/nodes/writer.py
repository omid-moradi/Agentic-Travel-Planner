"""The writer node - renders the final user-facing output.

No chain-of-thought is ever shown: only the itinerary, its sources, its confidence
labels and any warnings. In demo mode this is pure Python; from phase 5 the same
data is rendered by the web UI and an LLM may only add narrative prose on top of
the already-validated plan.
"""

from __future__ import annotations

from travel_planner.config.regions import IRAN_PROFILE, RegionProfile
from travel_planner.config.settings import Language
from travel_planner.schemas import DataStatus, Itinerary, TravelState

_STATUS_LABELS_FA = {
    DataStatus.CONFIRMED: "تأییدشده",
    DataStatus.ESTIMATED: "تقریبی",
    DataStatus.INFERRED: "استنباطی",
    DataStatus.UNAVAILABLE: "در دسترس نیست",
}

_STATUS_LABELS_EN = {
    DataStatus.CONFIRMED: "confirmed",
    DataStatus.ESTIMATED: "estimated",
    DataStatus.INFERRED: "inferred",
    DataStatus.UNAVAILABLE: "unavailable",
}


def _render_fa(itinerary: Itinerary, profile: RegionProfile) -> str:
    lines: list[str] = ["# برنامهٔ سفر", ""]
    if itinerary.total_cost is not None:
        lines.append(
            f"**بودجهٔ کل (تقریبی):** {profile.label_currency(itinerary.total_cost.amount)}"
            f" — {_STATUS_LABELS_FA[itinerary.total_cost.status]}"
        )
        lines.append("")
    for day in itinerary.days:
        lines.append(f"## روز {day.day_number} — {day.city} ({day.date.isoformat()})")
        if day.accommodation is not None:
            lines.append(f"- اقامت: {day.accommodation.name}")
        for activity in day.activities:
            label = _STATUS_LABELS_FA[activity.place.status]
            lines.append(
                f"- {activity.start_time}-{activity.end_time} "
                f"{activity.place.name} ({label})"
            )
        if day.daily_budget is not None:
            lines.append(
                f"- بودجهٔ روز: {profile.label_currency(day.daily_budget.amount)}"
            )
        for note in day.notes:
            lines.append(f"- ⚠ {note}")
        lines.append("")
    lines.append("> قیمت‌ها تقریبی هستند و ممکن است در سایت ارائه‌دهنده متفاوت باشند.")
    return "\n".join(lines)


def _render_en(itinerary: Itinerary, profile: RegionProfile) -> str:
    lines: list[str] = ["# Trip Plan", ""]
    if itinerary.total_cost is not None:
        lines.append(
            f"**Estimated total:** {profile.label_currency(itinerary.total_cost.amount)}"
            f" ({_STATUS_LABELS_EN[itinerary.total_cost.status]})"
        )
        lines.append("")
    for day in itinerary.days:
        lines.append(f"## Day {day.day_number} - {day.city} ({day.date.isoformat()})")
        if day.accommodation is not None:
            lines.append(f"- Stay: {day.accommodation.name}")
        for activity in day.activities:
            label = _STATUS_LABELS_EN[activity.place.status]
            lines.append(f"- {activity.start_time}-{activity.end_time} {activity.place.name} ({label})")
        if day.daily_budget is not None:
            lines.append(f"- Daily budget: {profile.label_currency(day.daily_budget.amount)}")
        for note in day.notes:
            lines.append(f"- Warning: {note}")
        lines.append("")
    lines.append("> Prices are estimates and may differ on the provider's site.")
    return "\n".join(lines)


def write_output(state: TravelState) -> dict[str, object]:
    """Render the validated itinerary in the requested language."""
    if state.itinerary is None:
        msg = "write_output called without an itinerary"
        raise ValueError(msg)

    profile = IRAN_PROFILE
    text = (
        _render_fa(state.itinerary, profile)
        if state.request.language is Language.FA
        else _render_en(state.itinerary, profile)
    )
    return {
        "messages": [
            *state.messages,
            {"role": "assistant", "content": text, "ts": ""},
        ],
        "current_step": "done",
    }
