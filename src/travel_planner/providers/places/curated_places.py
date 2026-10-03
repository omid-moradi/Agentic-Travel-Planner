"""Curated places provider - the checked-in dataset fallback (ADR-006).

Serves the same ``PlacesProvider`` interface as the scrapers, but from the
curated fixture set. Every record is CONFIRMED with the fixture source, and the
dataset is meant to be replaced by an admin-imported CSV/JSON with
``last_verified_at`` in a later phase.
"""

from __future__ import annotations

from travel_planner.data.fixtures.iran import SHIRAZ_PLACES, TEHRAN_PLACES
from travel_planner.providers.base import ProviderResult
from travel_planner.schemas import Coordinates, DataStatus, PlaceInfo

_DATASET: dict[str, list[PlaceInfo]] = {
    "tehran": TEHRAN_PLACES,
    "shiraz": SHIRAZ_PLACES,
}


class CuratedPlacesProvider:
    """Serve attractions from the curated dataset, never inventing anything."""

    name = "curated_places"

    def search_places(
        self, city: str, center: Coordinates, *, limit: int = 10
    ) -> ProviderResult:
        places = _DATASET.get(city.strip().lower())
        if not places:
            from travel_planner.errors import ProviderUnavailableError

            msg = f"{self.name}: no curated data for {city!r}"
            raise ProviderUnavailableError(msg)
        items = places[:limit]
        return ProviderResult(
            items=items,
            status=DataStatus.CONFIRMED,
            provider=self.name,
            note="curated dataset, last verified 2026-10-01",
        )
