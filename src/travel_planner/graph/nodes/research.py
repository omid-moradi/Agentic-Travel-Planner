"""Research nodes - fixture-backed in phase 2, provider-backed from phase 3.

Each node reads the typed ``TravelState`` and appends ``Finding`` objects with explicit
provenance. In demo mode every finding is either CONFIRMED (curated fixture with a
retrieval date) or INFERRED (documented heuristic). Nothing is invented.
"""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise

from travel_planner.data.fixtures.iran import (
    SHIRAZ_HOTELS,
    SHIRAZ_PLACES,
    SHIRAZ_RESTAURANTS,
    TEHRAN_HOTELS,
    TEHRAN_PLACES,
    TEHRAN_RESTAURANTS,
    estimated_price,
)
from travel_planner.schemas import (
    Coordinates,
    DataStatus,
    Finding,
    Source,
    TravelState,
)

#: City name -> fixture data. Case-insensitive lookup on the request destinations.
_CITY_FIXTURES: dict[str, dict[str, object]] = {
    "tehran": {
        "places": TEHRAN_PLACES,
        "hotels": TEHRAN_HOTELS,
        "restaurants": TEHRAN_RESTAURANTS,
        "center": Coordinates(lat=35.6892, lon=51.3890),
    },
    "shiraz": {
        "places": SHIRAZ_PLACES,
        "hotels": SHIRAZ_HOTELS,
        "restaurants": SHIRAZ_RESTAURANTS,
        "center": Coordinates(lat=29.6188, lon=52.5435),
    },
}

_FIXTURE_SOURCE = Source(
    name="curated fixture",
    url="https://github.com/omid-moradi/Agentic-Travel-Planner",
    retrieved_at=datetime(2026, 10, 1, 12, 0, 0),
)


def city_center(city: str) -> Coordinates:
    """Return the reference center point for a fixture city."""
    entry = _CITY_FIXTURES.get(city.lower())
    if entry is None:
        msg = f"No fixture data for city {city!r}"
        raise KeyError(msg)
    center = entry["center"]
    assert isinstance(center, Coordinates)
    return center


def _cities_for(state: TravelState) -> list[str]:
    """Return the canonical fixture names for the requested destinations."""
    wanted = [d.strip().lower() for d in state.request.destinations if d.strip()]
    matched = [c for c in wanted if c in _CITY_FIXTURES]
    # Fallback: at least one city so the graph always produces a plan.
    return matched or ["tehran"]


def _finding(
    category: str, summary: str, details: dict[str, object], status: DataStatus
) -> Finding:
    return Finding(
        category=category,
        summary=summary,
        details=details,
        status=status,
        source=_FIXTURE_SOURCE if status is DataStatus.CONFIRMED else None,
    )


# --------------------------------------------------------------------- nodes
def research_places(state: TravelState) -> dict[str, list[Finding]]:
    """Attractions per city, from the curated fixture set."""
    findings: list[Finding] = []
    for city in _cities_for(state):
        places = _CITY_FIXTURES[city]["places"]
        assert isinstance(places, list)
        findings.append(
            _finding(
                category="places",
                summary=f"{len(places)} confirmed attractions for {city.title()}",
                details={"city": city, "places": [p.model_dump() for p in places]},
                status=DataStatus.CONFIRMED,
            )
        )
    return {"places_findings": findings}


def research_accommodation(state: TravelState) -> dict[str, list[Finding]]:
    """Hotel options per city, from the curated fixture set."""
    findings: list[Finding] = []
    for city in _cities_for(state):
        hotels = _CITY_FIXTURES[city]["hotels"]
        assert isinstance(hotels, list)
        findings.append(
            _finding(
                category="accommodation",
                summary=f"{len(hotels)} hotel options for {city.title()}",
                details={"city": city, "hotels": [h.model_dump() for h in hotels]},
                status=DataStatus.CONFIRMED,
            )
        )
    return {"accommodation_findings": findings}


def research_restaurants(state: TravelState) -> dict[str, list[Finding]]:
    findings: list[Finding] = []
    for city in _cities_for(state):
        restaurants = _CITY_FIXTURES[city]["restaurants"]
        assert isinstance(restaurants, list)
        findings.append(
            _finding(
                category="restaurants",
                summary=f"{len(restaurants)} restaurants for {city.title()}",
                details={"city": city, "restaurants": [r.model_dump() for r in restaurants]},
                status=DataStatus.CONFIRMED,
            )
        )
    return {"restaurants_findings": findings}


#: Rough intercity distance/duration/cost for the fixture pairs (documented heuristic).
_INTERCITY: dict[tuple[str, str], tuple[float, int, float]] = {
    ("tehran", "shiraz"): (920.0, 90, 1_800_000.0),
    ("shiraz", "tehran"): (920.0, 90, 1_800_000.0),
}


def research_transport(state: TravelState) -> dict[str, list[Finding]]:
    """Intercity legs between consecutive destinations (flight estimate for demo)."""
    cities = _cities_for(state)
    findings: list[Finding] = []
    for origin, destination in pairwise(cities):
        leg = _INTERCITY.get((origin, destination))
        if leg is None:
            findings.append(
                _finding(
                    category="transport",
                    summary=f"No transport data for {origin} -> {destination}",
                    details={"origin": origin, "destination": destination},
                    status=DataStatus.UNAVAILABLE,
                )
            )
            continue
        distance_km, duration_min, cost_toman = leg
        findings.append(
            _finding(
                category="transport",
                summary=f"{origin.title()} -> {destination.title()} flight, ~{duration_min} min",
                details={
                    "origin": origin,
                    "destination": destination,
                    "mode": "flight",
                    "distance_km": distance_km,
                    "duration_minutes": duration_min,
                    "cost": estimated_price(cost_toman, "seasonal average, economy class"),
                },
                status=DataStatus.ESTIMATED,
            )
        )
    return {"transport_findings": findings}


#: Climate notes used until the live weather provider lands in phase 3.
_CLIMATE_NOTES = {
    "tehran": "Spring and autumn are mild; summers are hot and dry, winters cold.",
    "shiraz": "Spring (orange blossom) is ideal; summers are hot, winters mild.",
}


def research_weather(state: TravelState) -> dict[str, list[Finding]]:
    findings: list[Finding] = []
    for city in _cities_for(state):
        note = _CLIMATE_NOTES.get(city, "No climate data available.")
        findings.append(
            _finding(
                category="weather",
                summary=f"Climate note for {city.title()}",
                details={"city": city, "note": note, "kind": "climate_average"},
                status=DataStatus.INFERRED,
            )
        )
    return {"weather_findings": findings}


def research_events(state: TravelState) -> dict[str, list[Finding]]:
    """Events arrive with a real provider in phase 3; demo mode reports unavailable."""
    return {
        "events_findings": [
            _finding(
                category="events",
                summary="No event data available in demo mode",
                details={"reason": "events provider arrives in phase 3"},
                status=DataStatus.UNAVAILABLE,
            )
        ],
    }


def research_culture(state: TravelState) -> dict[str, list[Finding]]:
    return {
        "culture_findings": [
            _finding(
                category="culture",
                summary="Iran travel etiquette",
                details={
                    "dress_code": "Modest clothing required; women need a headscarf in public.",
                    "photography": "Ask before photographing people or government buildings.",
                },
                status=DataStatus.INFERRED,
            )
        ],
    }


def research_safety(state: TravelState) -> dict[str, list[Finding]]:
    return {
        "safety_findings": [
            _finding(
                category="safety",
                summary="General safety notes",
                details={
                    "cash": "International cards mostly do not work; bring enough cash.",
                    "emergency": "Tourist police (110) available in major cities.",
                },
                status=DataStatus.INFERRED,
            )
        ],
    }


def research_requirements(state: TravelState) -> dict[str, list[Finding]]:
    """Entry requirements are only ever advisory; a real source lands in phase 3/7."""
    return {
        "requirements_findings": [
            _finding(
                category="requirements",
                summary="Domestic trip - no visa requirements",
                details={"note": "Domestic travel requires only a national ID card."},
                status=DataStatus.INFERRED,
            )
        ],
    }

