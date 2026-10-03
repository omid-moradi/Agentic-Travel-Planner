"""The planner node - deterministic itinerary construction (ADR-008).

The LLM is not used here at all. Days are distributed across cities, venues are
ordered with the route optimizer, times are computed from visit durations, and the
budget is summed from per-activity estimates. The writer node may later add LLM
narrative on top, but the plan itself is reproducible Python.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from travel_planner.config.regions import Currency
from travel_planner.data.fixtures.iran import estimated_price
from travel_planner.graph.nodes.research import _CITY_FIXTURES, _cities_for
from travel_planner.optimizer.route import (
    estimate_daily_workload_hours,
    haversine_km,
    optimize_route,
)
from travel_planner.schemas import (
    Coordinates,
    DataStatus,
    DayActivity,
    DayPlan,
    Itinerary,
    PlaceInfo,
    PriceEstimate,
    RouteSegment,
    TransportMode,
    TravelState,
)

#: Day starts at 09:00; activities are separated by travel time.
_DAY_START_MINUTES = 9 * 60
#: Per-price-level entry cost in Toman (documented heuristic for demo mode).
_ENTRY_COST_BY_LEVEL = {1: 150_000.0, 2: 400_000.0, 3: 800_000.0, 4: 1_200_000.0}
#: Per-km local transport cost in Toman (taxi/metro blend).
_LOCAL_TRANSPORT_TOMAN_PER_KM = 45_000.0
#: Maximum active hours per day (workload cap, ADR-008).
_MAX_DAY_HOURS = 8.0
#: Hotel night cost by price level in Toman.
_HOTEL_NIGHT_COST = {1: 800_000.0, 2: 1_500_000.0, 3: 3_000_000.0, 4: 5_500_000.0}


def _minutes_to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _entry_cost(place: PlaceInfo) -> PriceEstimate:
    level = place.price_level or 1
    return estimated_price(_ENTRY_COST_BY_LEVEL[level], "typical entry fee")


def _walk_segment(origin: PlaceInfo, destination: PlaceInfo) -> RouteSegment:
    """A walking leg when the next venue is close, otherwise a taxi estimate."""
    assert origin.coordinates is not None and destination.coordinates is not None
    distance = haversine_km(origin.coordinates, destination.coordinates)
    # Walking 4.5 km/h; taxis average 25 km/h in city traffic.
    if distance <= 1.5:
        mode = TransportMode.WALK
        duration = max(5, round(distance / 4.5 * 60))
        cost = estimated_price(0.0, "walking")
    else:
        mode = TransportMode.TAXI
        duration = max(10, round(distance / 25 * 60))
        cost = estimated_price(distance * _LOCAL_TRANSPORT_TOMAN_PER_KM, "taxi estimate")
    return RouteSegment(
        origin=origin,
        destination=destination,
        mode=mode,
        distance_km=round(distance, 3),
        duration_minutes=duration,
        cost=cost,
    )


def _plan_one_day(
    day_number: int,
    day_date: date,
    city: str,
    places: list[PlaceInfo],
    hotel: PlaceInfo | None,
) -> DayPlan:
    """Build one day: order venues, schedule times, cap the workload."""
    entry = _CITY_FIXTURES[city]
    center = entry["center"]
    assert isinstance(center, Coordinates)

    # Start the route from the hotel if we have one, otherwise the city center.
    start = hotel.coordinates if hotel is not None and hotel.coordinates else center
    ordered = optimize_route(places, start)

    activities: list[DayActivity] = []
    cursor = _DAY_START_MINUTES
    previous: PlaceInfo | None = None

    for place in ordered:
        segment: RouteSegment | None = None
        if previous is not None and previous.coordinates and place.coordinates:
            segment = _walk_segment(previous, place)
            cursor += segment.duration_minutes
        duration = place.average_visit_duration_minutes or 60
        # Workload cap: stop adding activities once the day would exceed the cap.
        minutes_so_far = sum(
            a.place.average_visit_duration_minutes or 60 for a in activities
        )
        projected_hours = (
            minutes_so_far + duration + (segment.duration_minutes if segment else 0)
        ) / 60
        if projected_hours > _MAX_DAY_HOURS and activities:
            break
        activities.append(
            DayActivity(
                place=place,
                start_time=_minutes_to_hhmm(cursor),
                end_time=_minutes_to_hhmm(cursor + duration),
                transport_to_next=None,  # attached to the earlier activity below
                cost=_entry_cost(place),
            )
        )
        cursor += duration
        previous = place

    # Attach the leg to the next activity (transport_to_next lives on the earlier one).
    for i in range(len(activities) - 1):
        here = activities[i].place
        there = activities[i + 1].place
        if here.coordinates and there.coordinates:
            activities[i].transport_to_next = _walk_segment(here, there)

    daily_cost = sum(a.cost.amount for a in activities if a.cost)
    transport_cost = sum(
        a.transport_to_next.cost.amount
        for a in activities
        if a.transport_to_next and a.transport_to_next.cost
    )
    hotel_cost = 0.0
    if hotel is not None:
        level = hotel.price_level or 2
        hotel_cost = _HOTEL_NIGHT_COST[level]

    return DayPlan(
        day_number=day_number,
        date=day_date,
        city=city.title(),
        accommodation=hotel,
        activities=activities,
        daily_budget=estimated_price(
            daily_cost + transport_cost + hotel_cost,
            "entries + local transport + one hotel night",
        ),
        notes=(
            []
            if estimate_daily_workload_hours(activities) <= _MAX_DAY_HOURS
            else [f"Workload {estimate_daily_workload_hours(activities):.1f}h exceeds the cap"]
        ),
    )


def plan_itinerary(state: TravelState) -> dict[str, object]:
    """Distribute days across cities and build each day deterministically."""
    request = state.request
    cities = _cities_for(state)
    nights = request.duration_nights or max(1, len(cities))
    start = request.start_date or date.today()

    # Split the nights across the requested cities (earlier cities get the remainder).
    base, remainder = divmod(nights, len(cities))
    per_city = [base + (1 if i < remainder else 0) for i in range(len(cities))]

    days: list[DayPlan] = []
    day_number = 1
    cursor = start
    for city, city_nights in zip(cities, per_city, strict=True):
        entry = _CITY_FIXTURES[city]
        places = entry["places"]
        hotels = entry["hotels"]
        assert isinstance(places, list) and isinstance(hotels, list)
        hotel = hotels[0] if hotels else None
        for _ in range(city_nights):
            days.append(_plan_one_day(day_number, cursor, city, list(places), hotel))
            day_number += 1
            cursor += timedelta(days=1)

    total = sum(d.daily_budget.amount for d in days if d.daily_budget)
    itinerary = Itinerary(
        days=days,
        total_cost=PriceEstimate(
            amount=math.floor(total),
            currency=Currency.TOMAN,
            status=DataStatus.ESTIMATED,
            note="sum of estimated daily budgets",
        ),
    )
    return {
        "itinerary": itinerary,
        "itinerary_drafts": [*state.itinerary_drafts, itinerary],
        "current_step": "plan",
    }
