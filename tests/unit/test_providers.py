"""Unit tests for the provider registry, circuit breaker and graceful fallback."""

from __future__ import annotations

import pytest

from travel_planner.errors import ProviderUnavailableError
from travel_planner.providers.base import CircuitBreaker, ProviderRegistry
from travel_planner.schemas import Coordinates


class _GoodPlaces:
    name = "good_places"

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> str:
        return f"places for {city}"


class _BrokenPlaces:
    name = "broken_places"

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> str:
        msg = "site layout changed"
        raise ProviderUnavailableError(msg)


class _NonePlaces:
    name = "none_places"

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> str | None:
        return None


def _offline_settings():  # type: ignore[no-untyped-def]
    from travel_planner.config.settings import LLMProvider, Settings

    return Settings(llm_provider=LLMProvider.MOCK, _env_file=None)  # type: ignore[call-arg]


class TestProviderRegistry:
    def test_first_provider_wins(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_GoodPlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        assert registry.resolve("places", "search_places", "tehran", center) == "places for tehran"

    def test_falls_back_when_first_fails(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_BrokenPlaces(), _GoodPlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        assert registry.resolve("places", "search_places", "tehran", center) == "places for tehran"

    def test_falls_back_when_first_returns_none(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_NonePlaces(), _GoodPlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        assert registry.resolve("places", "search_places", "tehran", center) == "places for tehran"

    def test_whole_chain_failure_names_every_provider(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_BrokenPlaces(), _NonePlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        with pytest.raises(ProviderUnavailableError, match=r"broken_places.*none_places"):
            registry.resolve("places", "search_places", "tehran", center)

    def test_unregistered_capability_raises(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(ProviderUnavailableError, match="No providers registered"):
            registry.resolve("nothing", "any")

    def test_method_missing_is_a_fallback_not_a_crash(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_GoodPlaces()])  # no `geocode` method
        with pytest.raises(ProviderUnavailableError, match="no method"):
            registry.resolve("places", "geocode", "tehran")


class TestCircuitBreaker:
    def test_opens_after_threshold(self) -> None:
        breaker = CircuitBreaker(threshold=3, cooldown_seconds=300)
        for _ in range(3):
            breaker.record_failure("example.com")
        assert breaker.is_open("example.com") is True

    def test_success_resets(self) -> None:
        breaker = CircuitBreaker(threshold=3, cooldown_seconds=300)
        breaker.record_failure("example.com")
        breaker.record_failure("example.com")
        breaker.record_success("example.com")
        assert breaker.is_open("example.com") is False

    def test_half_open_after_cooldown(self) -> None:
        breaker = CircuitBreaker(threshold=1, cooldown_seconds=-1)  # cooldown already passed
        breaker.record_failure("example.com")
        assert breaker.is_open("example.com") is False  # half-open probe allowed


class TestRegistryFactory:
    def test_offline_registry_serves_places(self) -> None:
        from travel_planner.providers import build_registry

        registry = build_registry(_offline_settings())
        center = Coordinates(lat=35.6892, lon=51.3890)
        result = registry.resolve("places", "search_places", "tehran", center)
        assert result.provider == "curated_places"
        assert len(result.items) > 0

    def test_offline_registry_has_no_live_apis(self) -> None:
        from travel_planner.providers import build_registry

        registry = build_registry(_offline_settings())
        assert registry.chain_for("weather") == []
        assert registry.chain_for("routes") == []

    def test_curated_transport_only_answers_known_pairs(self) -> None:
        from travel_planner.providers import build_registry

        registry = build_registry(_offline_settings())
        # Tehran -> Shiraz is curated; the estimator refuses to invent the rest.
        result = registry.resolve("transport", "search_transport", "tehran", "shiraz")
        assert result.provider == "curated_transport"
        with pytest.raises(ProviderUnavailableError, match="refusing to invent"):
            registry.resolve("transport", "search_transport", "tehran", "tabriz")

    def test_unknown_provider_names_are_skipped_not_fatal(self) -> None:
        from travel_planner.config.settings import Settings
        from travel_planner.providers import build_registry

        settings = Settings(
            llm_provider="mock",
            places_providers=["does_not_exist", "curated"],
            _env_file=None,  # type: ignore[call-arg]
        )
        registry = build_registry(settings)
        assert len(registry.chain_for("places")) == 1


class TestRideFareEstimator:
    def test_fare_is_labelled_estimated(self) -> None:
        from travel_planner.providers.ride_fare.estimator import RideFareEstimator

        fare = RideFareEstimator(hour_of_day=12).estimate_fare(5.0, 20, "tehran")
        assert fare.status.value == "estimated"
        assert fare.amount > 0
        assert "tariff" in fare.note

    def test_peak_hours_cost_more(self) -> None:
        from travel_planner.providers.ride_fare.estimator import RideFareEstimator

        off_peak = RideFareEstimator(hour_of_day=12).estimate_fare(5.0, 20, "tehran")
        rush_hour = RideFareEstimator(hour_of_day=8).estimate_fare(5.0, 20, "tehran")
        assert rush_hour.amount > off_peak.amount

    def test_uncalibrated_city_falls_back_to_default_tariff(self) -> None:
        from travel_planner.providers.ride_fare.estimator import RideFareEstimator

        fare = RideFareEstimator(hour_of_day=12).estimate_fare(5.0, 20, "yazd")
        assert fare.amount > 0

