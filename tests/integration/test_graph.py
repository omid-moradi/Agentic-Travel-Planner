"""End-to-end graph tests - fully offline, the phase 2 acceptance gate.

Runs the whole LangGraph workflow against the curated fixtures and asserts that a
valid Tehran -> Shiraz trip comes out. No network, no API keys, no LLM.
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

import pytest

from travel_planner.config.settings import Language, Region
from travel_planner.graph import build_graph, initial_state, run_plan
from travel_planner.optimizer.route import estimate_daily_workload_hours
from travel_planner.schemas import DataStatus, TripRequest


def _request(**kwargs: object) -> TripRequest:
    defaults: dict[str, object] = {
        "raw_input": "Tehran to Shiraz, 3 nights",
        "region": Region.IRAN,
        "language": Language.FA,
        "destinations": ["Tehran", "Shiraz"],
        "start_date": date(2026, 11, 1),
        "duration_nights": 3,
        "travelers": 1,
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)  # type: ignore[arg-type]


class TestGraphShape:
    def test_graph_compiles(self) -> None:
        graph = build_graph()
        assert graph is not None

    def test_initial_state_defaults(self) -> None:
        state = initial_state(_request())
        assert state.current_step == "start"
        assert state.repair_count == 0


class TestFullRun:
    async def test_tehran_to_shiraz_offline(self) -> None:
        """The phase 2 gate: a valid multi-city trip, offline."""
        state = await run_plan(_request(), thread_id="gate-tehran-shiraz")

        assert state.is_valid, f"validation errors: {state.validation_issues}"
        assert state.itinerary is not None
        days = state.itinerary.days

        # Three nights, three days, in order, consecutive dates.
        assert len(days) == 3
        assert [d.day_number for d in days] == [1, 2, 3]
        for prev, curr in pairwise(days):
            assert curr.date - prev.date == timedelta(days=1)

        # Both requested cities are covered.
        cities = {d.city.lower() for d in days}
        assert "tehran" in cities
        assert "shiraz" in cities

        # Every day is feasible and every activity has a source status.
        for day in days:
            assert day.activities, f"day {day.day_number} has no activities"
            assert estimate_daily_workload_hours(day.activities) <= 8.0
            for activity in day.activities:
                assert activity.place.status is not None
                assert activity.start_time < activity.end_time

        # The total matches the sum of the daily budgets.
        daily_sum = sum(d.daily_budget.amount for d in days if d.daily_budget)
        assert state.itinerary.total_cost is not None
        assert state.itinerary.total_cost.amount == pytest.approx(daily_sum, abs=1)

        # The writer produced a Persian message.
        assert state.messages, "writer produced no message"
        assert "برنامهٔ سفر" in state.messages[-1]["content"]

        # Research findings were gathered with explicit provenance.
        assert len(state.places_findings) >= 2
        assert all(f.status is not None for f in state.places_findings)

    async def test_single_city_falls_back_to_tehran(self) -> None:
        """Unknown destinations never crash the graph; Tehran is the safe default."""
        state = await run_plan(
            _request(destinations=["Nowhere"], duration_nights=1),
            thread_id="gate-fallback",
        )
        assert state.itinerary is not None
        assert len(state.itinerary.days) == 1
        assert state.itinerary.days[0].city.lower() == "tehran"

    async def test_english_output(self) -> None:
        state = await run_plan(
            _request(language=Language.EN, duration_nights=1),
            thread_id="gate-english",
        )
        assert state.messages
        assert "Trip Plan" in state.messages[-1]["content"]

    async def test_budget_warning_when_total_exceeds_request(self) -> None:
        """A tight budget produces a warning, not a crash and not silent success."""
        state = await run_plan(
            _request(duration_nights=2, budget_total=100.0),
            thread_id="gate-budget",
        )
        assert state.itinerary is not None
        budget_warnings = [
            i for i in state.validation_issues if i.category == "budget"
        ]
        assert budget_warnings, "expected a budget warning for an impossible budget"

    async def test_unavailable_findings_are_labelled(self) -> None:
        """The events provider is absent in phase 2 and must say so honestly."""
        state = await run_plan(_request(), thread_id="gate-unavailable")
        assert any(
            f.status is DataStatus.UNAVAILABLE for f in state.events_findings
        ), "missing events data must be labelled unavailable, never invented"

    async def test_repair_loop_is_bounded(self) -> None:
        """Even a pathological request never loops more than max_repair_loops."""
        state = await run_plan(_request(), thread_id="gate-bounded")
        assert state.repair_count <= state.max_repair_loops
