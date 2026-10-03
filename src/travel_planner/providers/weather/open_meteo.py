"""Open-Meteo weather provider - a free, keyless, officially public API.

Terms: Open-Meteo is free for non-commercial use with no API key, and its
documentation explicitly permits automated access (fair-use limits apply).
This is the model for an "api_*" provider: no scraping, no key, cacheable.

Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from travel_planner.errors import ProviderUnavailableError
from travel_planner.schemas import Coordinates

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.open-meteo.com/v1"

#: WMO weather interpretation codes -> short label (documented in the API).
_WMO_LABELS: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snowfall",
    73: "moderate snowfall",
    75: "heavy snowfall",
    80: "rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


class OpenMeteoProvider:
    """Weather forecast via the public Open-Meteo API (no key, no scraping)."""

    name = "open_meteo"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=15.0)

    def get_weather(self, coordinates: Coordinates, date_iso: str) -> dict[str, object]:
        """Return a forecast summary for one location and date.

        Note: Open-Meteo serves a real forecast only for roughly the next 16
        days. Dates beyond that window are rejected by the API (HTTP 400), which
        surfaces here as ``ProviderUnavailableError`` - the honest answer, never
        a clamped or invented value (ADR-009).
        """
        params: dict[str, str | float] = {
            "latitude": coordinates.lat,
            "longitude": coordinates.lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "start_date": date_iso,
            "end_date": date_iso,
            "timezone": "auto",
        }
        try:
            response = self._client.get(f"{_BASE_URL}/forecast", params=params)
        except httpx.HTTPError as exc:
            msg = f"{self.name}: request failed: {exc}"
            raise ProviderUnavailableError(msg) from exc

        if response.status_code >= 400:
            msg = f"{self.name}: HTTP {response.status_code}"
            raise ProviderUnavailableError(msg)

        payload: dict[str, Any] = response.json()
        daily = payload.get("daily", {})
        try:
            code = int(daily["weather_code"][0])
            t_max = float(daily["temperature_2m_max"][0])
            t_min = float(daily["temperature_2m_min"][0])
            precipitation = float(daily["precipitation_sum"][0])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            msg = f"{self.name}: unexpected response shape: {exc}"
            raise ProviderUnavailableError(msg) from exc

        # The API clamps far-future dates to the end of its forecast window.
        returned_date = (daily.get("time") or [date_iso])[0]
        kind = "forecast" if str(returned_date) == date_iso else "clamped"

        return {
            "kind": kind,
            "date": str(returned_date),
            "label": _WMO_LABELS.get(code, f"wmo code {code}"),
            "temperature_max_c": t_max,
            "temperature_min_c": t_min,
            "precipitation_mm": precipitation,
            "source": "Open-Meteo (open-meteo.com)",
        }

    def close(self) -> None:
        self._client.close()
