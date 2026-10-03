"""Curated hotel and intercity-transport providers.

Serves the same interfaces the scrapers will serve, from the checked-in dataset.
Every price is labelled ``estimated`` with its basis; the dataset is replaced by
an admin-imported CSV/JSON (with ``last_verified_at``) in a later phase.
"""

from __future__ import annotations

from travel_planner.data.fixtures.iran import SHIRAZ_HOTELS, TEHRAN_HOTELS, estimated_price
from travel_planner.errors import ProviderUnavailableError
from travel_planner.providers.base import ProviderResult
from travel_planner.schemas import DataStatus, PlaceInfo

_HOTELS: dict[str, list[PlaceInfo]] = {
    "tehran": TEHRAN_HOTELS,
    "shiraz": SHIRAZ_HOTELS,
}

#: Nightly rate per price level in Toman (documented heuristic).
_NIGHTLY_BY_LEVEL = {1: 800_000.0, 2: 1_500_000.0, 3: 3_000_000.0, 4: 5_500_000.0}

#: Intercity transport estimates (Tehran <-> Shiraz), documented heuristic.
_INTERCITY: dict[tuple[str, str], dict[str, float]] = {
    ("tehran", "shiraz"): {"distance_km": 920.0, "duration_minutes": 90.0, "cost": 1_800_000.0},
    ("shiraz", "tehran"): {"distance_km": 920.0, "duration_minutes": 90.0, "cost": 1_800_000.0},
}


class CuratedHotelProvider:
    """Hotel options from the curated dataset."""

    name = "curated_hotels"

    def search_hotels(self, city: str, *, limit: int = 5) -> ProviderResult:
        hotels = _HOTELS.get(city.strip().lower())
        if not hotels:
            msg = f"{self.name}: no curated hotels for {city!r}"
            raise ProviderUnavailableError(msg)

        items = hotels[:limit]
        prices = [
            estimated_price(
                _NIGHTLY_BY_LEVEL.get(h.price_level or 2, 1_500_000.0),
                "nightly rate by price level (curated heuristic)",
            )
            for h in items
            if hasattr(h, "price_level")
        ]
        return ProviderResult(
            items=items,
            prices=prices,
            status=DataStatus.CONFIRMED,
            provider=self.name,
            note="curated dataset, last verified 2026-10-01",
        )


class CuratedTransportProvider:
    """Intercity transport options from the curated dataset."""

    name = "curated_transport"

    def search_transport(self, origin: str, destination: str) -> ProviderResult:
        key = (origin.strip().lower(), destination.strip().lower())
        leg = _INTERCITY.get(key)
        if leg is None:
            msg = f"{self.name}: no curated transport for {origin!r} -> {destination!r}"
            raise ProviderUnavailableError(msg)

        return ProviderResult(
            prices=[
                estimated_price(leg["cost"], "seasonal average, economy flight class")
            ],
            raw={
                "origin": origin,
                "destination": destination,
                "mode": "flight",
                "distance_km": leg["distance_km"],
                "duration_minutes": leg["duration_minutes"],
            },
            status=DataStatus.ESTIMATED,
            provider=self.name,
            note="curated dataset, last verified 2026-10-01",
        )


class TransportEstimator:
    """Formula-based intercity fallback when the dataset has no entry."""

    name = "estimator_transport"

    #: Toman per km for bus / train / flight blended (documented heuristic).
    _PER_KM = 1_500.0
    _BASE = 300_000.0

    def search_transport(self, origin: str, destination: str) -> ProviderResult:
        # Without a distance table we cannot honestly estimate an arbitrary pair.
        msg = (
            f"{self.name}: no distance basis for {origin!r} -> {destination!r}; "
            "refusing to invent a price"
        )
        raise ProviderUnavailableError(msg)


