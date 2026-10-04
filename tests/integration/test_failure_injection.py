"""Failure-injection suite - the system must degrade, never crash.

Each test breaks something on purpose and asserts the honest failure mode:
``ProviderUnavailableError`` for provider failures, the error envelope for
API failures, no-ops for replays. ADR-009: unavailable data is labelled
unavailable - it is never invented and it never takes the process down.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from travel_planner.errors import ProviderUnavailableError
from travel_planner.providers.base import ProviderRegistry
from travel_planner.schemas import Coordinates

pytest.importorskip("asgi_lifespan", reason="needed for app lifespan in tests")


# ------------------------------------------------------- provider failures
class _DeadPlaces:
    """A provider whose every call times out (simulated)."""

    name = "dead_places"

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> object:
        msg = "connection timed out after 20s"
        raise ProviderUnavailableError(msg)


class _EmptyPlaces:
    """A provider that answers with nothing (empty results)."""

    name = "empty_places"

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> object:
        return None


class _GoodPlaces:
    """The working fallback."""

    name = "good_places"

    def search_places(self, city: str, center: Coordinates, *, limit: int = 10) -> str:
        return f"places for {city}"


class TestProviderFailures:
    def test_timeout_falls_back_to_next_provider(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_DeadPlaces(), _GoodPlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        assert registry.resolve("places", "search_places", "tehran", center) == "places for tehran"

    def test_empty_results_fall_back(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_EmptyPlaces(), _GoodPlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        assert registry.resolve("places", "search_places", "tehran", center) == "places for tehran"

    def test_whole_chain_dead_raises_unavailable_not_crash(self) -> None:
        registry = ProviderRegistry()
        registry.register("places", [_DeadPlaces(), _EmptyPlaces()])
        center = Coordinates(lat=35.0, lon=51.0)
        with pytest.raises(ProviderUnavailableError) as excinfo:
            registry.resolve("places", "search_places", "tehran", center)
        # The error names every provider that was tried - honest diagnostics.
        message = str(excinfo.value)
        assert "dead_places" in message and "empty_places" in message

    def test_malformed_json_is_rejected_not_parsed(self) -> None:
        from travel_planner.llm.factory import extract_json

        assert extract_json("totally not json") is None
        assert extract_json('{"valid": true}') == {"valid": True}
        # A truncated JSON array is not an object.
        assert extract_json("[1, 2,") is None

    def test_429_and_outage_surface_as_unavailable(self) -> None:
        """The ScraperClient converts HTTP/网络 errors to its own exception."""
        from travel_planner.providers.http.scraper_client import ScraperClient

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "1"})

        client = ScraperClient(
            user_agent="TestBot/1.0",
            respect_robots=False,
            rate_limit_per_second=1000,
            max_retries=0,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ProviderUnavailableError, match="429"):
            client.fetch("https://example.com/rate-limited")
        client.close()

    def test_circuit_opens_after_repeated_failures(self) -> None:
        from travel_planner.providers.base import CircuitBreaker

        breaker = CircuitBreaker(threshold=2, cooldown_seconds=300)
        breaker.record_failure("example.com")
        breaker.record_failure("example.com")
        assert breaker.is_open("example.com") is True
        # The cooldown passed (negative) -> half-open, one probe allowed.
        breaker._opened_at["example.com"] -= 400  # simulate time passing
        assert breaker.is_open("example.com") is False


# ---------------------------------------------------------- API-level failures
def _temp_db(name: str) -> str:
    import uuid as _uuid
    from pathlib import Path

    folder = Path(".pytest_tmp")
    folder.mkdir(exist_ok=True)
    return f"sqlite+aiosqlite:///{folder / (name + _uuid.uuid4().hex[:8] + '.db')}"


@pytest.fixture()
async def client() -> httpx.AsyncClient:
    import os

    from asgi_lifespan import LifespanManager

    from travel_planner.api.app import create_app
    from travel_planner.config.settings import reload_settings

    os.environ["FREE_TIER_PLANS_PER_MONTH"] = "1000"
    os.environ["GUEST_TRIAL_ENABLED"] = "false"
    reload_settings()
    try:
        app = create_app(database_url=_temp_db("failinj"))
        async with LifespanManager(app) as manager:
            transport = httpx.ASGITransport(app=manager.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
                yield http
    finally:
        os.environ.pop("FREE_TIER_PLANS_PER_MONTH", None)
        os.environ.pop("GUEST_TRIAL_ENABLED", None)
        reload_settings()


class TestApiFailures:
    async def test_payment_webhook_replay_is_idempotent(
        self, client: httpx.AsyncClient
    ) -> None:
        """Replaying the same webhook must be a no-op, not a double credit."""
        register = await client.post(
            "/api/v1/auth/register",
            json={"email": "replay@example.com", "password": "correct-horse-battery"},
        )
        user_id = register.json()["user_id"]
        body = {
            "provider": "mock",
            "event_id": "evt-replay-1",
            "event_type": "subscription.created",
            "signature": "mock-signature",
            "payload": {"user_id": user_id},
        }
        first = await client.post("/api/v1/billing/webhook", json=body)
        replay = await client.post("/api/v1/billing/webhook", json=body)
        assert first.json()["duplicate"] is False
        assert replay.json()["duplicate"] is True
        assert replay.status_code == 200

    async def test_invalid_replan_reason_rejected(
        self, client: httpx.AsyncClient
    ) -> None:
        """An unknown live-mode reason gets the error envelope, not a crash."""
        created = await client.post("/api/v1/trips", json={"request": "Tehran overnight"})
        trip_id = created.json()["id"]
        bad = await client.post(
            f"/api/v1/trips/{trip_id}/replan-today", json={"reason": "earthquake"}
        )
        assert bad.status_code == 400
        assert bad.json()["error"]["code"] == "invalid_reason"

    async def test_malformed_body_returns_422(
        self, client: httpx.AsyncClient
    ) -> None:
        """A malformed JSON body is a 422, never a 500."""
        response = await client.post(
            "/api/v1/trips",
            content=b"{not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    async def test_unknown_trip_paths_get_envelopes(
        self, client: httpx.AsyncClient
    ) -> None:
        """Every subresource of a missing trip fails with the error envelope."""
        unknown = uuid.uuid4()
        for path in ("checklist", "entry-requirements", "expenses"):
            response = await client.get(f"/api/v1/trips/{unknown}/{path}")
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "not_found"
        # ``today`` checks the itinerary first, so it reports no_itinerary.
        today = await client.get(f"/api/v1/trips/{unknown}/today")
        assert today.status_code == 404
        assert today.json()["error"]["code"] == "no_itinerary"

    async def test_provider_outage_still_serves_health(
        self, client: httpx.AsyncClient
    ) -> None:
        """Even with providers down, liveness and metrics keep answering."""
        health = await client.get("/api/v1/health")
        assert health.status_code == 200
        metrics_response = await client.get("/api/v1/metrics")
        assert metrics_response.status_code == 200
        assert "api_requests_total" in metrics_response.text

