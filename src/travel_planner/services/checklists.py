"""Packing list and document checklist - deterministic, LLM-free.

Generated from the trip's region, season and duration. Every item carries a
``reason`` so the user understands why it is suggested - and the document
checklist for international trips always includes the "verify with official
source" reminder (ADR-009: entry rules are advisory, never asserted).
"""

from __future__ import annotations

from datetime import date

from travel_planner.db.models import Trip

#: Season per month index (1-12) in the northern hemisphere.
_SEASON_BY_MONTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

_BASE_PACKING = [
    ("passport-or-id", "Identification (original + a photocopy/photo)"),
    ("phone-charger", "Phone charger and a power bank"),
    ("power-adapter", "Power adapter for the destination's sockets"),
    ("first-aid", "Small first-aid kit: painkillers, plasters, personal medication"),
    ("money-cash", "Cash - cards are not always accepted everywhere"),
]

_WINTER = [
    ("warm-coat", "Warm coat - winter in the destination"),
    ("layers", "Thermal layers and a hat/gloves"),
]
_SUMMER = [
    ("sunscreen", "Sunscreen and sunglasses"),
    ("hat", "A sun hat"),
    ("water-bottle", "Reusable water bottle"),
]
_RAINY = [
    ("umbrella", "Compact umbrella - rain is common this season"),
    ("waterproof-shoes", "Waterproof or quick-dry shoes"),
]

# Iran-specific: the master prompt's local context (dress code, prayer times).
_IRAN_EXTRAS = [
    ("dress-modest", "Modest clothing; women need a headscarf in public (Iran)"),
    ("comfortable-shoes", "Comfortable walking shoes - historic sites involve lots of walking"),
    ("snapp-cash", "Cash for local ride apps - international cards mostly do not work in Iran"),
]

#: Documents for domestic Iran vs international travel.
_IRAN_DOCS = [
    ("national-id", "National ID card (original)"),
    ("insurance", "Travel insurance is recommended"),
]
_INTERNATIONAL_DOCS = [
    ("passport", "Passport - many destinations require 6 months of validity beyond the stay"),
    ("visa", "Visa or e-visa - check the destination's official portal"),
    ("insurance", "Travel health insurance covering the whole stay"),
    ("tickets", "Flight/transport tickets and hotel bookings (printed + digital)"),
]


def season_for(start_date: date | None) -> str:
    """The trip's season; autumn by default when the date is unknown."""
    if start_date is None:
        return "autumn"
    return _SEASON_BY_MONTH.get(start_date.month, "autumn")


def packing_list(trip: Trip) -> list[dict[str, str]]:
    """Suggested packing items with a reason each, ordered deterministically."""
    season = season_for(trip.start_date)
    items = list(_BASE_PACKING)

    if season == "winter":
        items.extend(_WINTER)
    elif season == "summer":
        items.extend(_SUMMER)
    elif season == "spring":
        items.append(_RAINY[0])  # umbrella only; spring showers
    else:
        items.extend(_RAINY)

    if trip.region == "iran":
        items.extend(_IRAN_EXTRAS)
    if trip.duration_nights and trip.duration_nights >= 5:
        items.append(("laundry-bag", "A laundry bag - a longer trip means washing clothes"))

    return [{"id": key, "item": text, "reason": f"suggested for a {season} trip"}
            for key, text in items]


def document_checklist(trip: Trip) -> dict[str, object]:
    """Required documents plus the mandatory official-source warning."""
    docs = _IRAN_DOCS if trip.region == "iran" else _INTERNATIONAL_DOCS
    return {
        "documents": [
            {"id": key, "document": text} for key, text in docs
        ],
        "warning": (
            "Entry and visa rules change. Always verify the requirements with the "
            "destination's official government source before you travel."
        ),
        "status": "advisory",
    }
