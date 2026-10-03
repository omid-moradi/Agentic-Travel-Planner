"""Provider abstraction: one Protocol per capability, a registry, graceful degradation.

Design rules (ADR-006):

* Every capability is a ``Protocol`` with an ordered fallback chain selected from env,
  e.g. ``HOTELS_PROVIDERS=scraper_site_a,curated,estimator``. Swapping a scraper for an
  official API means changing that one env line - no agent, graph or schema changes.
* A provider that cannot answer raises :class:`ProviderUnavailableError`; the registry
  then tries the next provider in the chain. The failure is recorded, never hidden.
* A provider must never invent data. "I could not get it" is a valid answer; a made-up
  price is not (ADR-009).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from travel_planner.errors import ProviderUnavailableError
from travel_planner.schemas import (
    Coordinates,
    DataStatus,
    PlaceInfo,
    PriceEstimate,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """What a capability provider returned, with its provenance attached."""

    items: list[PlaceInfo] = field(default_factory=list)
    prices: list[PriceEstimate] = field(default_factory=list)
    raw: dict[str, object] = field(default_factory=dict)
    status: DataStatus = DataStatus.CONFIRMED
    provider: str = ""
    note: str = ""


@runtime_checkable
class PlacesProvider(Protocol):
    """Search points of interest near a location."""

    name: str

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> ProviderResult:
        ...


@runtime_checkable
class GeocodeProvider(Protocol):
    """Resolve a free-text query to coordinates."""

    name: str

    def geocode(self, query: str) -> Coordinates | None:
        ...


@runtime_checkable
class RouteProvider(Protocol):
    """Route and travel time between two points."""

    name: str

    def route(self, origin: Coordinates, destination: Coordinates) -> dict[str, object]:
        ...


@runtime_checkable
class WeatherProvider(Protocol):
    """Forecast or climate summary for a location."""

    name: str

    def get_weather(self, coordinates: Coordinates, date_iso: str) -> dict[str, object]:
        ...


@runtime_checkable
class HotelProvider(Protocol):
    """Hotel options for a city."""

    name: str

    def search_hotels(self, city: str, *, limit: int = 5) -> ProviderResult:
        ...


@runtime_checkable
class TransportProvider(Protocol):
    """Intercity transport options between two cities."""

    name: str

    def search_transport(self, origin: str, destination: str) -> ProviderResult:
        ...


@runtime_checkable
class RideFareProvider(Protocol):
    """Estimated intra-city ride fare."""

    name: str

    def estimate_fare(self, distance_km: float, duration_minutes: int, city: str) -> PriceEstimate:
        ...


class CircuitBreaker:
    """Per-source breaker: after ``threshold`` consecutive failures, stay open.

    A breaker that is open fails fast instead of hammering a dead or changed site -
    the registry then falls down the chain immediately.
    """

    def __init__(self, threshold: int = 3, cooldown_seconds: float = 300.0) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def is_open(self, key: str) -> bool:
        """True when the source should not be called right now."""
        opened = self._opened_at.get(key)
        if opened is None:
            return False
        if time.monotonic() - opened >= self._cooldown:
            # Half-open: allow one probe.
            self._opened_at.pop(key, None)
            self._failures[key] = self._threshold - 1
            return False
        return True

    def record_success(self, key: str) -> None:
        self._failures.pop(key, None)
        self._opened_at.pop(key, None)

    def record_failure(self, key: str) -> None:
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        if count >= self._threshold:
            self._opened_at[key] = time.monotonic()
            logger.warning("circuit opened for %s after %d failures", key, count)


class ProviderRegistry:
    """Ordered fallback chain per capability, resolved from provider instances.

    ``register`` attaches concrete providers under a capability name; ``resolve``
    walks the chain and returns the first provider that answers. Every fallback is
    logged so the trace shows exactly which provider served the request.
    """

    def __init__(self) -> None:
        self._chains: dict[str, list[object]] = {}

    def register(self, capability: str, providers: list[object]) -> None:
        """Set the fallback chain for a capability (order matters)."""
        self._chains[capability] = list(providers)

    def chain_for(self, capability: str) -> list[object]:
        return list(self._chains.get(capability, []))

    def resolve(self, capability: str, call: str, *args: object, **kwargs: object) -> object:
        """Call ``call`` on each provider in turn until one answers.

        Raises :class:`ProviderUnavailableError` only when the whole chain failed,
        with the per-provider reasons attached.
        """
        providers = self._chains.get(capability)
        if not providers:
            msg = f"No providers registered for capability {capability!r}"
            raise ProviderUnavailableError(msg)

        failures: list[str] = []
        for provider in providers:
            name = getattr(provider, "name", type(provider).__name__)
            method = getattr(provider, call, None)
            if method is None:
                failures.append(f"{name}: no method {call!r}")
                continue
            try:
                result = method(*args, **kwargs)
            except ProviderUnavailableError as exc:
                failures.append(f"{name}: {exc}")
                logger.info("provider fallback %s/%s failed: %s", capability, name, exc)
                continue
            if result is None:
                failures.append(f"{name}: returned None")
                continue
            logger.info("provider %s.%s answered via %s", capability, call, name)
            return result

        msg = f"All providers failed for {capability}.{call}: " + "; ".join(failures)
        raise ProviderUnavailableError(msg)

