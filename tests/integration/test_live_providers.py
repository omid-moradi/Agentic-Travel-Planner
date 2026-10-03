"""Opt-in live smoke tests against the free, keyless public APIs.

Marked ``live``; they skip when the network is unavailable or ``LLM_PROVIDER=mock``
(demo mode). These document the verified behaviour of each live provider
(the phase 3 gate requires "documented live smoke tests").

Run with::

    pytest -m live
"""

from __future__ import annotations

import datetime as dt

import pytest

from travel_planner.config.settings import LLMProvider, Settings
from travel_planner.errors import ProviderUnavailableError
from travel_planner.providers.routes.osrm import OsrmRouteProvider
from travel_planner.providers.weather.open_meteo import OpenMeteoProvider
from travel_planner.schemas import Coordinates

pytestmark = pytest.mark.live

pytest.importorskip("httpx", reason="httpx is required for live provider tests")


def _live_settings() -> Settings:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    if settings.llm_provider is LLMProvider.MOCK:
        pytest.skip("LLM_PROVIDER=mock means offline demo mode; skipping live tests")
    return settings


TEHRAN = Coordinates(lat=35.6892, lon=51.3890)
SHIRAZ = Coordinates(lat=29.6188, lon=52.5435)


class TestOpenMeteoLive:
    def test_forecast_for_near_future(self) -> None:
        _live_settings()
        provider = OpenMeteoProvider()
        try:
            tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
            weather = provider.get_weather(TEHRAN, tomorrow)
            assert weather["kind"] == "forecast"
            assert isinstance(weather["temperature_max_c"], float)
            assert weather["label"]
        finally:
            provider.close()

    def test_far_future_is_honestly_unavailable(self) -> None:
        """A date beyond the forecast window is refused, never guessed (ADR-009)."""
        _live_settings()
        provider = OpenMeteoProvider()
        try:
            far = (dt.date.today() + dt.timedelta(days=60)).isoformat()
            with pytest.raises(ProviderUnavailableError):
                provider.get_weather(TEHRAN, far)
        finally:
            provider.close()

    def test_bad_request_raises(self) -> None:
        _live_settings()
        provider = OpenMeteoProvider()
        try:
            with pytest.raises(ProviderUnavailableError):
                provider.get_weather(TEHRAN, "not-a-date")
        finally:
            provider.close()


class TestOsrmLive:
    def test_route_tehran_to_shiraz(self) -> None:
        _live_settings()
        provider = OsrmRouteProvider()
        try:
            route = provider.route(TEHRAN, SHIRAZ)
            distance = route["distance_km"]
            duration = route["duration_minutes"]
            assert isinstance(distance, float)
            assert 700 < distance < 1100, f"unexpected distance: {distance}"
            assert 400 < duration < 1200, f"unexpected duration: {duration}"
        finally:
            provider.close()

    def test_short_route_is_reasonable(self) -> None:
        _live_settings()
        provider = OsrmRouteProvider()
        try:
            near = Coordinates(lat=35.6900, lon=51.3900)
            route = provider.route(TEHRAN, near)
            assert 0 <= route["distance_km"] < 5
        finally:
            provider.close()
