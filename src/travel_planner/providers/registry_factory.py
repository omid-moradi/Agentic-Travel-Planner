"""Assemble the provider registry from settings.

The chains come from env (e.g. ``HOTELS_PROVIDERS=curated,estimator``), so
swapping a scraper for an official API is a configuration change, not a code
change (ADR-006). Short names ("curated", "estimator", ...) are resolved
per-capability, because "curated hotels" and "curated places" are different
classes. In offline/demo mode the live-API providers are left out so the graph
still runs with zero network.
"""

from __future__ import annotations

import logging
from typing import Any

from travel_planner.config.settings import Settings, get_settings
from travel_planner.providers.base import ProviderRegistry
from travel_planner.providers.hotels.curated_hotels import (
    CuratedHotelProvider,
    CuratedTransportProvider,
    TransportEstimator,
)
from travel_planner.providers.places.curated_places import CuratedPlacesProvider
from travel_planner.providers.ride_fare.estimator import RideFareEstimator

logger = logging.getLogger(__name__)


def _offline_factories() -> dict[tuple[str, str], Any]:
    """(capability, short name) -> class, for providers that need no network."""
    return {
        ("places", "fixture"): CuratedPlacesProvider,
        ("places", "curated"): CuratedPlacesProvider,
        ("places", "curated_places"): CuratedPlacesProvider,
        ("places", "scraper_jsonld_attractions"): "scraper",  # needs a configured client
        ("hotels", "curated"): CuratedHotelProvider,
        ("hotels", "curated_hotels"): CuratedHotelProvider,
        ("transport", "curated"): CuratedTransportProvider,
        ("transport", "curated_transport"): CuratedTransportProvider,
        ("transport", "estimator"): TransportEstimator,
        ("ride_fare", "estimator"): RideFareEstimator,
    }


def _live_factories(settings: Settings) -> dict[tuple[str, str], Any]:
    """(capability, short name) -> instance, for providers that use the network."""
    from travel_planner.providers.routes.osrm import OsrmRouteProvider
    from travel_planner.providers.weather.open_meteo import OpenMeteoProvider

    return {
        ("weather", "open_meteo"): OpenMeteoProvider(),
        ("routes", "osrm"): OsrmRouteProvider(base_url=settings.osrm_base_url),
    }


def build_registry(settings: Settings | None = None) -> ProviderRegistry:
    """Build the registry with chains resolved from the environment."""
    cfg = settings or get_settings()
    offline = _offline_factories()
    live = {} if cfg.is_offline else _live_factories(cfg)

    capability_settings: list[tuple[str, list[str]]] = [
        ("places", cfg.places_providers),
        ("hotels", cfg.hotels_providers),
        ("transport", cfg.transport_providers),
        ("ride_fare", cfg.ride_fare_providers),
        ("weather", cfg.weather_providers),
        ("routes", cfg.routes_providers),
        ("geocode", cfg.geocode_providers),
        ("restaurants", cfg.restaurants_providers),
        ("events", cfg.events_providers),
        ("currency", cfg.currency_providers),
    ]

    registry = ProviderRegistry()
    resolved: dict[str, list[str]] = {}
    for capability, names in capability_settings:
        providers: list[object] = []
        found_names: list[str] = []
        for name in names:
            instance: object | None = None
            if (capability, name) in live:
                instance = live[(capability, name)]
            elif (capability, name) in offline:
                entry = offline[(capability, name)]
                if entry == "scraper":
                    # Scrapers need a configured ScraperClient + target URL and
                    # are only enabled explicitly (see docs/data-sources.md).
                    logger.warning("scraper provider %r needs explicit setup; skipping", name)
                    continue
                instance = entry()
            if instance is None:
                # Unknown or not-yet-built providers are logged and skipped -
                # the chain must still work with whatever exists.
                logger.warning("skipping unavailable provider %r for %s", name, capability)
                continue
            providers.append(instance)
            found_names.append(getattr(instance, "name", name))
        if providers:
            registry.register(capability, providers)
            resolved[capability] = found_names

    logger.info("provider registry built: %s", resolved)
    return registry

