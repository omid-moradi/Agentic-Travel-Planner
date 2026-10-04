"""Unit tests for the reason-aware, day-scoped Live Mode transforms."""

from __future__ import annotations

from datetime import date, timedelta
from typing import cast

from travel_planner.graph.nodes.planner import _plan_one_day
from travel_planner.graph.nodes.research import _CITY_FIXTURES
from travel_planner.schemas import DayPlan, Itinerary, PlaceInfo, TransportMode
from travel_planner.services.live_mode import apply_reason, merge_patched_today


def _tehran_day(day_number: int = 1, day_date: date | None = None) -> DayPlan:
    entry = _CITY_FIXTURES["tehran"]
    places = cast(list[PlaceInfo], entry["places"])
    hotels = cast(list[PlaceInfo], entry["hotels"])
    hotel = hotels[0] if hotels else None
    return _plan_one_day(
        day_number, day_date or date.today(), "tehran", list(places), hotel
    )


class TestApplyReason:
    def test_tired_keeps_at_most_three_activities(self) -> None:
        lighter = apply_reason(_tehran_day(), "tired")
        assert len(lighter.activities) <= 3
        # The kept day is rescheduled from the canonical 09:00 start.
        assert lighter.activities[0].start_time == "09:00"
        for earlier, later in zip(lighter.activities, lighter.activities[1:], strict=False):
            assert earlier.start_time < later.start_time

    def test_closed_venue_drops_the_first_activity(self) -> None:
        day = _tehran_day()
        patched = apply_reason(day, "closed_venue")
        assert len(patched.activities) == max(0, len(day.activities) - 1)
        if patched.activities:
            assert patched.activities[0].place.name != day.activities[0].place.name

    def test_running_late_shifts_the_start(self) -> None:
        patched = apply_reason(_tehran_day(), "running_late")
        assert patched.activities[0].start_time == "11:00"

    def test_rain_leaves_no_walking_legs(self) -> None:
        patched = apply_reason(_tehran_day(), "rain")
        for activity in patched.activities:
            leg = activity.transport_to_next
            assert leg is None or leg.mode is TransportMode.TAXI

    def test_budget_changed_keeps_only_cheap_venues(self) -> None:
        patched = apply_reason(_tehran_day(), "budget_changed")
        assert patched.activities
        levels = {a.place.price_level or 1 for a in patched.activities}
        assert levels <= {1, 2} or len(patched.activities) == 1

    def test_every_reason_recomputes_the_daily_budget(self) -> None:
        day = _tehran_day()
        for reason in ("rain", "closed_venue", "running_late", "tired", "budget_changed"):
            patched = apply_reason(day, reason)
            assert patched.daily_budget is not None
            entries = sum(a.cost.amount for a in patched.activities if a.cost)
            assert patched.daily_budget.amount >= entries


class TestMergePatchedToday:
    def test_only_today_is_patched_other_days_kept(self) -> None:
        today = date.today()
        old = Itinerary(
            days=[
                _tehran_day(1, today),
                _tehran_day(2, today + timedelta(days=1)),
                _tehran_day(3, today + timedelta(days=2)),
            ],
        )
        fresh = old.model_copy(deep=True)
        merged = merge_patched_today(old, fresh, today, "tired")

        assert len(merged.days) == 3
        assert len(merged.days[0].activities) <= 3
        # The other days are the traveller's existing days, untouched.
        assert merged.days[1] == old.days[1]
        assert merged.days[2] == old.days[2]

    def test_total_is_recomputed_from_the_daily_budgets(self) -> None:
        today = date.today()
        old = Itinerary(
            days=[_tehran_day(1, today), _tehran_day(2, today + timedelta(days=1))],
        )
        merged = merge_patched_today(old, old.model_copy(deep=True), today, "tired")
        assert merged.total_cost is not None
        expected = sum(
            d.daily_budget.amount for d in merged.days if d.daily_budget
        )
        assert merged.total_cost.amount == int(expected)  # floored
