"""OSRM route provider - a free, keyless, self-hostable routing API.

The public demo server (router.project-osrm.org) is used by default; a
self-hosted instance can be configured through ``OSRM_BASE_URL`` which is the
recommended production path (the demo server has no SLA).

Docs: https://project-osrm.org/docs/api.ms
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from travel_planner.errors import ProviderUnavailableError
from travel_planner.schemas import Coordinates

logger = logging.getLogger(__name__)


class OsrmRouteProvider:
    """Road distance and duration between two coordinates via OSRM."""

    name = "osrm"

    def __init__(self, base_url: str = "https://router.project-osrm.org", client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=15.0)

    def route(self, origin: Coordinates, destination: Coordinates) -> dict[str, object]:
        """Return distance (km) and duration (minutes) for the driving route."""
        path = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        params = {"overview": "false"}
        url = f"{self._base_url}/route/v1/driving/{path}"
        try:
            response = self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            msg = f"{self.name}: request failed: {exc}"
            raise ProviderUnavailableError(msg) from exc

        if response.status_code >= 400:
            msg = f"{self.name}: HTTP {response.status_code}"
            raise ProviderUnavailableError(msg)

        payload: dict[str, Any] = response.json()
        if payload.get("code") != "Ok":
            msg = f"{self.name}: API returned code {payload.get('code')!r}"
            raise ProviderUnavailableError(msg)

        try:
            route = payload["routes"][0]
            distance_km = round(float(route["distance"]) / 1000.0, 3)
            duration_minutes = round(float(route["duration"]) / 60.0)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            msg = f"{self.name}: unexpected response shape: {exc}"
            raise ProviderUnavailableError(msg) from exc

        return {
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
            "source": "OSRM (project-osrm.org)",
        }

    def close(self) -> None:
        self._client.close()
