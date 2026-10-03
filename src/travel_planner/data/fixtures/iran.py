"""Curated fixture data for demo mode and offline tests.

These exist so the product can generate a plausible Tehran -> Shiraz trip with zero
network calls. Real providers (phase 3) replace these when available.
"""

from __future__ import annotations

from datetime import datetime

from travel_planner.config.regions import Currency
from travel_planner.schemas import (
    Coordinates,
    DataStatus,
    OpeningHours,
    PlaceInfo,
    PriceEstimate,
    Source,
)

_FIXTURE_SOURCE = Source(
    name="curated fixture",
    url="https://github.com/omid-moradi/Agentic-Travel-Planner",
    retrieved_at=datetime(2026, 10, 1, 12, 0, 0),
)

# =============================== Tehran ===============================
TEHRAN_PLACES: list[PlaceInfo] = [
    PlaceInfo(
        name="Golestan Palace",
        place_type="attraction",
        address="Arg Square, Tehran",
        coordinates=Coordinates(lat=35.6795, lon=51.4209),
        description="UNESCO World Heritage Site, former royal Qajar complex",
        opening_hours=OpeningHours(monday="09:00-17:00", tuesday="09:00-17:00", wednesday="09:00-17:00", thursday="09:00-17:00", friday="closed", saturday="09:00-17:00", sunday="09:00-17:00"),
        average_visit_duration_minutes=120,
        rating=4.7,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="National Museum of Iran",
        place_type="museum",
        address="Si-e Tir St, Tehran",
        coordinates=Coordinates(lat=35.6868, lon=51.4204),
        description="Ancient Persian artifacts and archaeological treasures",
        opening_hours=OpeningHours(monday="09:00-17:00", tuesday="09:00-17:00", wednesday="09:00-17:00", thursday="09:00-17:00", friday="closed", saturday="09:00-17:00", sunday="09:00-17:00"),
        average_visit_duration_minutes=90,
        rating=4.5,
        price_level=1,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Grand Bazaar",
        place_type="shopping",
        address="15 Khordad Square, Tehran",
        coordinates=Coordinates(lat=35.6724, lon=51.4289),
        description="Historic covered market, spices, carpets, handicrafts",
        opening_hours=OpeningHours(always_open=False, monday="08:00-20:00", tuesday="08:00-20:00", wednesday="08:00-20:00", thursday="08:00-20:00", friday="closed", saturday="08:00-20:00", sunday="08:00-20:00"),
        average_visit_duration_minutes=120,
        rating=4.6,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Milad Tower",
        place_type="landmark",
        address="Hemmat Highway, Tehran",
        coordinates=Coordinates(lat=35.7447, lon=51.3755),
        description="Tallest structure in Iran, observation deck and restaurant",
        opening_hours=OpeningHours(always_open=False, monday="10:00-22:00", tuesday="10:00-22:00", wednesday="10:00-22:00", thursday="10:00-22:00", friday="10:00-22:00", saturday="10:00-22:00", sunday="10:00-22:00"),
        average_visit_duration_minutes=90,
        rating=4.4,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
]

# =============================== Shiraz ===============================
SHIRAZ_PLACES: list[PlaceInfo] = [
    PlaceInfo(
        name="Nasir al-Mulk Mosque (Pink Mosque)",
        place_type="attraction",
        address="Lotf Ali Khan Zand St, Shiraz",
        coordinates=Coordinates(lat=29.6061, lon=52.5481),
        description="Stunning stained glass windows, best light in the morning",
        opening_hours=OpeningHours(monday="08:00-17:00", tuesday="08:00-17:00", wednesday="08:00-17:00", thursday="08:00-17:00", friday="08:00-17:00", saturday="08:00-17:00", sunday="08:00-17:00"),
        average_visit_duration_minutes=60,
        rating=4.9,
        price_level=1,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Persepolis",
        place_type="historical_site",
        address="60 km northeast of Shiraz",
        coordinates=Coordinates(lat=29.9356, lon=52.8910),
        description="Ancient Achaemenid capital, UNESCO World Heritage",
        opening_hours=OpeningHours(always_open=False, monday="08:00-17:00", tuesday="08:00-17:00", wednesday="08:00-17:00", thursday="08:00-17:00", friday="08:00-17:00", saturday="08:00-17:00", sunday="08:00-17:00"),
        average_visit_duration_minutes=180,
        rating=5.0,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Eram Garden",
        place_type="garden",
        address="Eram Boulevard, Shiraz",
        coordinates=Coordinates(lat=29.6287, lon=52.5533),
        description="Persian garden with cypress trees and a historic mansion",
        opening_hours=OpeningHours(monday="08:00-19:00", tuesday="08:00-19:00", wednesday="08:00-19:00", thursday="08:00-19:00", friday="08:00-19:00", saturday="08:00-19:00", sunday="08:00-19:00"),
        average_visit_duration_minutes=90,
        rating=4.6,
        price_level=1,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Tomb of Hafez",
        place_type="monument",
        address="Hafez St, Shiraz",
        coordinates=Coordinates(lat=29.6275, lon=52.5667),
        description="Mausoleum of the beloved Persian poet, peaceful garden setting",
        opening_hours=OpeningHours(always_open=False, monday="08:00-21:00", tuesday="08:00-21:00", wednesday="08:00-21:00", thursday="08:00-21:00", friday="08:00-21:00", saturday="08:00-21:00", sunday="08:00-21:00"),
        average_visit_duration_minutes=60,
        rating=4.8,
        price_level=1,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Vakil Bazaar",
        place_type="shopping",
        address="Zand Street, Shiraz",
        coordinates=Coordinates(lat=29.6108, lon=52.5467),
        description="Traditional bazaar with handicrafts, spices and local goods",
        opening_hours=OpeningHours(monday="08:00-20:00", tuesday="08:00-20:00", wednesday="08:00-20:00", thursday="08:00-20:00", friday="closed", saturday="08:00-20:00", sunday="08:00-20:00"),
        average_visit_duration_minutes=90,
        rating=4.5,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
]

TEHRAN_HOTELS: list[PlaceInfo] = [
    PlaceInfo(
        name="Espinas Palace Hotel",
        place_type="hotel",
        address="Saadat Abad, Tehran",
        coordinates=Coordinates(lat=35.7648, lon=51.3976),
        description="5-star luxury hotel with modern amenities",
        rating=4.6,
        price_level=4,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Ferdowsi Grand Hotel",
        place_type="hotel",
        address="Ferdowsi Avenue, Tehran",
        coordinates=Coordinates(lat=35.6998, lon=51.4085),
        description="Mid-range hotel near Grand Bazaar, good value",
        rating=4.2,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
]

SHIRAZ_HOTELS: list[PlaceInfo] = [
    PlaceInfo(
        name="Zandiyeh Hotel",
        place_type="hotel",
        address="Zand Boulevard, Shiraz",
        coordinates=Coordinates(lat=29.6091, lon=52.5391),
        description="4-star hotel in the city center, walking distance to attractions",
        rating=4.4,
        price_level=3,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Arg Hotel",
        place_type="hotel",
        address="Karim Khan Street, Shiraz",
        coordinates=Coordinates(lat=29.6115, lon=52.5421),
        description="Budget-friendly, traditional Persian decor",
        rating=4.0,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
]

TEHRAN_RESTAURANTS: list[PlaceInfo] = [
    PlaceInfo(
        name="Moslem Restaurant",
        place_type="restaurant",
        address="Enqelab St, Tehran",
        coordinates=Coordinates(lat=35.7020, lon=51.4052),
        description="Famous for traditional Persian stews (khoresh)",
        rating=4.7,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Nayeb Restaurant",
        place_type="restaurant",
        address="30 Tir St, Tehran",
        coordinates=Coordinates(lat=35.6914, lon=51.4182),
        description="Historic restaurant, kebabs and traditional dishes",
        rating=4.5,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
]

SHIRAZ_RESTAURANTS: list[PlaceInfo] = [
    PlaceInfo(
        name="Sharzeh Restaurant",
        place_type="restaurant",
        address="Rudaki St, Shiraz",
        coordinates=Coordinates(lat=29.6175, lon=52.5543),
        description="Traditional Persian cuisine in a garden setting",
        rating=4.6,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
    PlaceInfo(
        name="Haft Khan Restaurant",
        place_type="restaurant",
        address="Zand St, Shiraz",
        coordinates=Coordinates(lat=29.6102, lon=52.5412),
        description="Rooftop dining, grilled meats and local specialties",
        rating=4.4,
        price_level=2,
        status=DataStatus.CONFIRMED,
        source=_FIXTURE_SOURCE,
    ),
]


def estimated_price(amount_toman: float, note: str = "") -> PriceEstimate:
    """Helper to create an estimated price in Toman."""
    return PriceEstimate(
        amount=amount_toman,
        currency=Currency.TOMAN,
        status=DataStatus.ESTIMATED,
        note=note,
    )


ALL_FIXTURES = {
    "tehran_places": TEHRAN_PLACES,
    "shiraz_places": SHIRAZ_PLACES,
    "tehran_hotels": TEHRAN_HOTELS,
    "shiraz_hotels": SHIRAZ_HOTELS,
    "tehran_restaurants": TEHRAN_RESTAURANTS,
    "shiraz_restaurants": SHIRAZ_RESTAURANTS,
}
