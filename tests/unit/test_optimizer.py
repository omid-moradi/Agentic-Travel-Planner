"""Unit tests for the deterministic optimizer (ADR-008 - no LLM anywhere)."""

from __future__ import annotations

import pytest

from travel_planner.optimizer.route import (
    cluster_by_distance,
    estimate_daily_workload_hours,
    haversine_km,
    is_workload_feasible,
    nearest_neighbour_order,
    optimize_route,
    two_opt_improve,
)
from travel_planner.schemas import (
    Coordinates,
    DayActivity,
    PlaceInfo,
    TransportMode,
)


def _place(name: str, lat: float, lon: float, duration: int = 60) -> PlaceInfo:
    return PlaceInfo(
        name=name,
        place_type="attraction",
        coordinates=Coordinates(lat=lat, lon=lon),
        average_visit_duration_minutes=duration,
    )


class TestHaversine:
    def test_same_point_is_zero(self) -> None:
        c = Coordinates(lat=35.7, lon=51.4)
        assert haversine_km(c, c) == pytest.approx(0.0)

    def test_known_short_distance(self) -> None:
        # Golestan Palace -> National Museum, ~0.8 km in reality.
        a = Coordinates(lat=35.6795, lon=51.4209)
        b = Coordinates(lat=35.6868, lon=51.4204)
        assert 0.5 < haversine_km(a, b) < 1.2

    def test_tehran_to_shiraz_is_about_680km(self) -> None:
        tehran = Coordinates(lat=35.6892, lon=51.3890)
        shiraz = Coordinates(lat=29.6188, lon=52.5435)
        assert 650 < haversine_km(tehran, shiraz) < 720


class TestClustering:
    def test_nearby_places_cluster(self) -> None:
        places = [
            _place("a", 35.6795, 51.4209),
            _place("b", 35.6868, 51.4204),  # ~0.8 km from a
        ]
        clusters = cluster_by_distance(places, max_distance_km=1.5)
        assert len(clusters) == 1
        assert len(clusters[0].places) == 2

    def test_far_places_separate(self) -> None:
        places = [
            _place("a", 35.68, 51.42),
            _place("b", 35.75, 51.37),   # ~8 km away
        ]
        clusters = cluster_by_distance(places, max_distance_km=1.5)
        assert len(clusters) == 2

    def test_places_without_coordinates_are_skipped(self) -> None:
        nowhere = PlaceInfo(name="nowhere", place_type="attraction")
        clusters = cluster_by_distance([nowhere], max_distance_km=1.5)
        assert clusters == []


class TestNearestNeighbour:
    def test_visits_nearest_first(self) -> None:
        start = Coordinates(lat=35.70, lon=51.40)
        places = [
            _place("far", 35.60, 51.40),
            _place("near", 35.705, 51.405),
            _place("mid", 35.65, 51.40),
        ]
        ordered = nearest_neighbour_order(places, start)
        assert ordered[0].name == "near"

    def test_empty_input(self) -> None:
        assert nearest_neighbour_order([], Coordinates(lat=0, lon=0)) == []


class TestTwoOpt:
    def test_short_route_is_not_made_worse(self) -> None:
        places = [
            _place("a", 35.68, 51.42),
            _place("b", 35.75, 51.37),
            _place("c", 35.60, 51.50),
        ]
        improved = two_opt_improve(places)

        def total(route: list[PlaceInfo]) -> float:
            return sum(
                haversine_km(route[i].coordinates, route[i + 1].coordinates)  # type: ignore[arg-type]
                for i in range(len(route) - 1)
            )

        assert total(improved) <= total(places) + 1e-9

    def test_short_list_returned_unchanged(self) -> None:
        places = [_place("a", 35.68, 51.42)]
        assert two_opt_improve(places) == places


class TestWorkload:
    def _activity(self, duration: int, travel: int = 0) -> DayActivity:
        place = _place("p", 35.68, 51.42, duration)
        segment = None
        if travel:
            from travel_planner.schemas import RouteSegment

            segment = RouteSegment(
                origin=place,
                destination=place,
                mode=TransportMode.WALK,
                distance_km=0.5,
                duration_minutes=travel,
            )
        return DayActivity(place=place, start_time="09:00", end_time="10:00", transport_to_next=segment)

    def test_hours_summed(self) -> None:
        activities = [self._activity(120), self._activity(90, travel=30)]
        assert estimate_daily_workload_hours(activities) == pytest.approx(4.0)

    def test_feasibility_boundary(self) -> None:
        assert is_workload_feasible([self._activity(240)], max_hours=4.0)
        assert not is_workload_feasible([self._activity(241)], max_hours=4.0)


class TestOptimizeRoute:
    def test_all_places_returned(self) -> None:
        places = [
            _place("a", 35.68, 51.42),
            _place("b", 35.75, 51.37),
            _place("c", 35.60, 51.50),
        ]
        result = optimize_route(places, Coordinates(lat=35.7, lon=51.4))
        assert len(result) == 3
        assert {p.name for p in result} == {"a", "b", "c"}
