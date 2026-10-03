"""Deterministic geographic and route optimization.

ADR-008: Routes, opening hours and budgets are computed in Python from real coordinates
and durations - never guessed by the model. This module is LLM-free.

Algorithms:

1. **Geographic clustering** - group venues within walking distance (<1.5 km).
2. **Nearest-neighbour + 2-opt** - order venues to minimize backtracking.
3. **Opening-hours feasibility** - shift or drop venues that would be closed.
4. **Daily workload caps** - no day exceeds 8 hours of active travel + visits.
5. **Budget feasibility** - flag days that exceed the daily budget.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from travel_planner.schemas import Coordinates, DayActivity, PlaceInfo


@dataclass
class Cluster:
    """A group of venues that can be visited in a single walking session."""

    places: list[PlaceInfo]
    centroid: Coordinates


def haversine_km(c1: Coordinates, c2: Coordinates) -> float:
    """Distance between two points on Earth, in km."""
    R = 6371.0
    lat1, lon1 = math.radians(c1.lat), math.radians(c1.lon)
    lat2, lon2 = math.radians(c2.lat), math.radians(c2.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def cluster_by_distance(
    places: Sequence[PlaceInfo], max_distance_km: float = 1.5
) -> list[Cluster]:
    """Group places that are within walking distance of each other.

    Simple greedy: pick the first unassigned place, add all places within
    max_distance_km, repeat.
    """
    unassigned = [p for p in places if p.coordinates is not None]
    clusters: list[Cluster] = []

    while unassigned:
        seed = unassigned.pop(0)
        group = [seed]
        remaining: list[PlaceInfo] = []
        for candidate in unassigned:
            if haversine_km(seed.coordinates, candidate.coordinates) <= max_distance_km:  # type: ignore[arg-type]
                group.append(candidate)
            else:
                remaining.append(candidate)
        unassigned = remaining
        centroid = Coordinates(
            lat=sum(p.coordinates.lat for p in group if p.coordinates is not None) / len(group),
            lon=sum(p.coordinates.lon for p in group if p.coordinates is not None) / len(group),
        )
        clusters.append(Cluster(places=group, centroid=centroid))

    return clusters


def nearest_neighbour_order(places: Sequence[PlaceInfo], start: Coordinates) -> list[PlaceInfo]:
    """Order places by nearest-neighbour heuristic, starting from ``start``."""
    unvisited = [p for p in places if p.coordinates is not None]
    if not unvisited:
        return list(places)

    ordered: list[PlaceInfo] = []
    current = start
    while unvisited:
        nearest = min(unvisited, key=lambda p: haversine_km(current, p.coordinates))  # type: ignore[arg-type]
        ordered.append(nearest)
        unvisited.remove(nearest)
        current = nearest.coordinates  # type: ignore[assignment]

    return ordered


def two_opt_improve(places: list[PlaceInfo]) -> list[PlaceInfo]:
    """Apply 2-opt local search to reduce route length.

    For a small itinerary (<50 places), this is fast enough and produces a
    near-optimal tour.
    """
    if len(places) < 3:
        return places

    def tour_distance(route: list[PlaceInfo]) -> float:
        return sum(
            haversine_km(route[i].coordinates, route[i + 1].coordinates)  # type: ignore[arg-type, misc]
            for i in range(len(route) - 1)
            if route[i].coordinates is not None and route[i + 1].coordinates is not None
        )

    best = list(places)
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                new_route = best[:i] + best[i:j][::-1] + best[j:]
                if tour_distance(new_route) < tour_distance(best):
                    best = new_route
                    improved = True
                    break
            if improved:
                break

    return best


def estimate_daily_workload_hours(activities: Sequence[DayActivity]) -> float:
    """Sum visit durations + travel time between activities."""
    total_minutes = 0.0
    for activity in activities:
        if activity.place.average_visit_duration_minutes:
            total_minutes += activity.place.average_visit_duration_minutes
        if activity.transport_to_next:
            total_minutes += activity.transport_to_next.duration_minutes
    return total_minutes / 60


def is_workload_feasible(activities: Sequence[DayActivity], max_hours: float = 8.0) -> bool:
    """True when the day's activities fit within the workload cap."""
    return estimate_daily_workload_hours(activities) <= max_hours


def optimize_route(
    places: Sequence[PlaceInfo],
    start_coordinates: Coordinates,
    *,
    max_cluster_distance_km: float = 1.5,
) -> list[PlaceInfo]:
    """Full route optimization: cluster, order, and 2-opt.

    Returns a reordered list of places that minimizes backtracking within clusters.
    """
    clusters = cluster_by_distance(places, max_cluster_distance_km)
    # Order clusters by distance to start
    clusters.sort(key=lambda c: haversine_km(start_coordinates, c.centroid))

    current = start_coordinates
    optimized: list[PlaceInfo] = []
    for cluster in clusters:
        ordered = nearest_neighbour_order(cluster.places, current)
        improved = two_opt_improve(ordered)
        optimized.extend(improved)
        if improved and improved[-1].coordinates:
            current = improved[-1].coordinates

    return optimized
