"""API end-to-end tests - the phase 4 gate.

Runs the real FastAPI app over httpx's ASGI transport against a throwaway SQLite
file, executing the real graph. No network, no mocking of our own code.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytest.importorskip("asgi_lifespan", reason="needed for app lifespan in tests")


def _temp_db(name: str) -> str:
    """A project-local throwaway SQLite path (the OS temp dir is not writable here)."""
    import uuid
    from pathlib import Path

    folder = Path(".pytest_tmp")
    folder.mkdir(exist_ok=True)
    return f"sqlite+aiosqlite:///{folder / (name + uuid.uuid4().hex[:8] + '.db')}"


@pytest.fixture(scope="module")
async def client() -> httpx.AsyncClient:
    """The app plus a fresh SQLite database, one per module."""
    from asgi_lifespan import LifespanManager

    from travel_planner.api.app import create_app

    app = create_app(database_url=_temp_db("api_e2e"))
    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http:
            yield http


class TestHealth:
    async def test_health(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_ready(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        assert "version" in response.json()

    async def test_request_id_header(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.headers.get("x-request-id")

    async def test_openapi_documented(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert "/api/v1/trips" in paths
        assert "/api/v1/trips/{trip_id}/replan" in paths
        assert "/api/v1/share/{token}" in paths


class TestTripLifecycle:
    """Create -> plan -> fetch -> replan: the core golden path."""

    async def test_create_trip_plans_it_immediately(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/trips",
            json={
                "request": "Tehran to Shiraz, 3 nights, cultural trip",
                "region": "iran",
                "language": "en",
                "duration_nights": 3,
                "travelers": 2,
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "done"
        trip_id: str = body["id"]
        assert uuid.UUID(trip_id)

        itinerary = await client.get(f"/api/v1/trips/{trip_id}/itinerary")
        assert itinerary.status_code == 200
        payload = itinerary.json()
        assert payload["is_valid"] is True
        assert payload["version"] == 1
        assert len(payload["payload"]["days"]) == 3

        messages = await client.get(f"/api/v1/trips/{trip_id}/messages")
        assert messages.status_code == 200
        roles = [m["role"] for m in messages.json()["items"]]
        assert "assistant" in roles

        trace = await client.get(f"/api/v1/trips/{trip_id}/trace")
        assert trace.status_code == 200
        assert len(trace.json()["items"]) >= 4

    async def test_get_trip(self, client: httpx.AsyncClient) -> None:
        created = await client.post(
            "/api/v1/trips", json={"request": "Shiraz for 2 nights"}
        )
        trip_id = created.json()["id"]
        fetched = await client.get(f"/api/v1/trips/{trip_id}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == trip_id

    async def test_list_trips(self, client: httpx.AsyncClient) -> None:
        listing = await client.get("/api/v1/trips")
        assert listing.status_code == 200
        assert listing.json()["count"] >= 1

    async def test_replan_creates_a_new_version(self, client: httpx.AsyncClient) -> None:
        created = await client.post(
            "/api/v1/trips", json={"request": "Tehran for 1 night"}
        )
        trip_id = created.json()["id"]
        before = (await client.get(f"/api/v1/trips/{trip_id}/itinerary")).json()

        replanned = await client.post(f"/api/v1/trips/{trip_id}/replan")
        assert replanned.status_code == 200
        after = (await client.get(f"/api/v1/trips/{trip_id}/itinerary")).json()

        # The old version is kept as history, never overwritten.
        assert after["version"] == before["version"] + 1
        assert replanned.json()["status"] == "done"

    async def test_usage_records_the_plan(self, client: httpx.AsyncClient) -> None:
        usage = await client.get("/api/v1/usage")
        assert usage.status_code == 200
        kinds = {item["kind"] for item in usage.json()["items"]}
        assert "plan" in kinds


class TestShareLinks:
    async def test_share_round_trip(self, client: httpx.AsyncClient) -> None:
        created = await client.post(
            "/api/v1/trips", json={"request": "Shiraz weekend"}
        )
        trip_id = created.json()["id"]

        shared = await client.post(f"/api/v1/trips/{trip_id}/share")
        assert shared.status_code == 201, shared.text
        token = shared.json()["token"]

        public = await client.get(f"/api/v1/share/{token}")
        assert public.status_code == 200
        body = public.json()
        assert body["read_only"] is True
        assert body["itinerary"] is not None

        # Idempotent: a second call returns the same token.
        again = await client.post(f"/api/v1/trips/{trip_id}/share")
        assert again.json()["token"] == token

    async def test_unknown_token_404s(self, client: httpx.AsyncClient) -> None:
        missing = await client.get("/api/v1/share/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"


class TestErrorEnvelope:
    async def test_invalid_trip_id_shape(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/trips/not-a-uuid")
        assert response.status_code == 400
        envelope = response.json()["error"]
        assert envelope["code"] == "invalid_id"
        assert envelope["request_id"]

    async def test_missing_trip_404_envelope(self, client: httpx.AsyncClient) -> None:
        unknown = uuid.uuid4()
        response = await client.get(f"/api/v1/trips/{unknown}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_validation_error_envelope(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            "/api/v1/trips", json={"request": "", "duration_nights": 99}
        )
        assert response.status_code == 422


class TestRateLimiting:
    async def test_rate_limit_returns_429(self) -> None:
        """A tiny limit trips the in-process limiter, verified end to end."""
        from asgi_lifespan import LifespanManager

        from travel_planner.api.app import create_app

        app = create_app(database_url=_temp_db("api_rl"), rate_limit=3)
        async with LifespanManager(app) as manager:
            transport = httpx.ASGITransport(app=manager.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
                codes = [(await http.get("/api/v1/health")).status_code for _ in range(6)]
                assert 429 in codes

