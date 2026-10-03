"""Attractions scraper built on JSON-LD - the reference scraper pattern.

This demonstrates the contract every scraper in this codebase follows:

* it declares its source, base URL and parser version,
* it fetches only through the shared :class:`ScraperClient`,
* it parses structured JSON-LD first (robust) rather than CSS chains (brittle),
* a record without a name or coordinates is rejected, not half-parsed,
* failures surface as ``ProviderUnavailableError`` so the registry can fall back.

The target site is a **fixture** in tests and an example deployment in production;
it is deliberately not a real third-party site until its robots.txt and ToS have
been reviewed and recorded in ``docs/data-sources.md``.
"""

from __future__ import annotations

import logging

from travel_planner.errors import ProviderUnavailableError
from travel_planner.providers.base import ProviderResult
from travel_planner.providers.http.jsonld import find_jsonld_by_type, jsonld_to_placeinfo
from travel_planner.providers.http.scraper_client import ScraperClient
from travel_planner.schemas import (
    Coordinates,
    DataStatus,
    PlaceInfo,
)

logger = logging.getLogger(__name__)

PARSER_VERSION = "1"


class JsonLdAttractionsScraper:
    """Scrape attractions from a site that publishes schema.org JSON-LD."""

    name = "scraper_jsonld_attractions"

    def __init__(self, client: ScraperClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def search_places(
        self, city: str, center: Coordinates, *, limit: int = 10
    ) -> ProviderResult:
        """Fetch the city page and extract ``TouristAttraction`` records."""
        url = f"{self._base_url}/{city.lower()}/attractions"
        html = self._client.fetch(url, ttl_seconds=86_400)

        nodes = find_jsonld_by_type(html, "TouristAttraction")
        places: list[PlaceInfo] = []
        for node in nodes[:limit]:
            kwargs = jsonld_to_placeinfo(
                node, place_type="attraction", source_name=self.name
            )
            if kwargs is None:
                logger.info("skipping unnamed record from %s", self.name)
                continue
            # Records without coordinates are rejected: the optimizer needs them.
            coordinates = kwargs.get("coordinates")
            if not isinstance(coordinates, dict) or "lat" not in coordinates:
                logger.info("skipping record without coordinates: %r", kwargs.get("name"))
                continue
            places.append(
                PlaceInfo(
                    name=str(kwargs["name"]),
                    place_type="attraction",
                    address=str(kwargs.get("address", "")),
                    coordinates=Coordinates(
                        lat=float(coordinates["lat"]), lon=float(coordinates["lon"])
                    ),
                    description=str(kwargs.get("description", "")),
                    status=DataStatus.CONFIRMED,
                )
            )

        if not places:
            msg = f"{self.name}: no usable TouristAttraction records at {url}"
            raise ProviderUnavailableError(msg)

        return ProviderResult(
            items=places,
            status=DataStatus.CONFIRMED,
            provider=self.name,
            note=f"parsed with jsonld v{PARSER_VERSION}",
        )
