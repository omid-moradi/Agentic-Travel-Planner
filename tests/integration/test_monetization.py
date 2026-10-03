"""Monetization tests - the phase 6 gate.

Covers: auth (register/login/JWT/roles), entitlement quotas (guest trial,
free plan limits, the 402 envelope), webhook idempotency and the subscription
state machine, affiliate disclosure, and admin authorization.

All offline: the real app, a throwaway SQLite, httpx ASGI transport.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytest.importorskip("asgi_lifespan", reason="needed for app lifespan in tests")


def _temp_db(name: str) -> str:
    import uuid as _uuid
    from pathlib import Path

    folder = Path(".pytest_tmp")
    folder.mkdir(exist_ok=True)
    return f"sqlite+aiosqlite:///{folder / (name + _uuid.uuid4().hex[:8] + '.db')}"


@pytest.fixture()
async def fresh_client() -> httpx.AsyncClient:
    """A fresh app with a fresh database per test (isolation matters here)."""
    from asgi_lifespan import LifespanManager

    from travel_planner.api.app import create_app

    app = create_app(database_url=_temp_db("monetize"))
    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
            yield http


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    async def test_register_login_me(self, fresh_client: httpx.AsyncClient) -> None:
        register = await fresh_client.post(
            "/api/v1/auth/register",
            json={"email": "sara@example.com", "password": "correct-horse-battery"},
        )
        assert register.status_code == 201, register.text
        token = register.json()["access_token"]

        me = await fresh_client.get("/api/v1/auth/me", headers=_auth_header(token))
        assert me.status_code == 200
        assert me.json()["email"] == "sara@example.com"
        assert me.json()["is_admin"] is False

        login = await fresh_client.post(
            "/api/v1/auth/login",
            json={"email": "sara@example.com", "password": "correct-horse-battery"},
        )
        assert login.status_code == 200
        assert login.json()["access_token"]

    async def test_duplicate_email_rejected(self, fresh_client: httpx.AsyncClient) -> None:
        body = {"email": "dup@example.com", "password": "correct-horse-battery"}
        first = await fresh_client.post("/api/v1/auth/register", json=body)
        second = await fresh_client.post("/api/v1/auth/register", json=body)
        assert first.status_code == 201
        assert second.status_code == 409

    async def test_wrong_password_401(self, fresh_client: httpx.AsyncClient) -> None:
        await fresh_client.post(
            "/api/v1/auth/register",
            json={"email": "ali@example.com", "password": "correct-horse-battery"},
        )
        login = await fresh_client.post(
            "/api/v1/auth/login",
            json={"email": "ali@example.com", "password": "wrong-password!"},
        )
        assert login.status_code == 401

    async def test_me_without_token_401(self, fresh_client: httpx.AsyncClient) -> None:
        me = await fresh_client.get("/api/v1/auth/me")
        assert me.status_code == 401

    async def test_bad_token_rejected(self, fresh_client: httpx.AsyncClient) -> None:
        me = await fresh_client.get("/api/v1/auth/me", headers=_auth_header("not-a-jwt"))
        assert me.status_code == 401


class TestEntitlements:
    async def test_guest_gets_exactly_one_plan(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        """The master prompt's guest trial: one free plan without signup."""
        first = await fresh_client.post(
            "/api/v1/trips", json={"request": "Shiraz weekend"}
        )
        assert first.status_code == 201
        second = await fresh_client.post(
            "/api/v1/trips", json={"request": "Tehran weekend"}
        )
        assert second.status_code == 402
        envelope = second.json()["error"]
        assert envelope["code"] == "quota_exceeded"
        assert envelope["details"]["plan"] == "guest"
        assert envelope["details"]["limit"] == 1

    async def test_free_account_gets_the_monthly_limit(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        register = await fresh_client.post(
            "/api/v1/auth/register",
            json={"email": "nima@example.com", "password": "correct-horse-battery"},
        )
        token = register.json()["access_token"]
        headers = _auth_header(token)

        status = await fresh_client.get("/api/v1/billing/status", headers=headers)
        assert status.status_code == 200
        limits = status.json()["limits"]

        # Plans up to the limit succeed; the next one is refused with 402.
        created = 0
        rejected = None
        for _ in range(limits["plans_per_month"] + 1):
            response = await fresh_client.post(
                "/api/v1/trips",
                json={"request": "Isfahan day trip"},
                headers=headers,
            )
            if response.status_code == 201:
                created += 1
            else:
                rejected = response
                break
        assert created == limits["plans_per_month"]
        assert rejected is not None and rejected.status_code == 402

    async def test_billing_status_reports_guest_plan(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        status = await fresh_client.get("/api/v1/billing/status")
        assert status.json()["plan"] == "guest"
        assert status.json()["authenticated"] is False


class TestWebhooks:
    async def _register(self, client: httpx.AsyncClient) -> str:
        register = await client.post(
            "/api/v1/auth/register",
            json={"email": "payer@example.com", "password": "correct-horse-battery"},
        )
        return str(register.json()["user_id"])

    async def test_webhook_activates_subscription(self, fresh_client: httpx.AsyncClient) -> None:
        user_id = await self._register(fresh_client)
        webhook = await fresh_client.post(
            "/api/v1/billing/webhook",
            json={
                "provider": "mock",
                "event_id": "evt-001",
                "event_type": "subscription.created",
                "signature": "mock-signature",
                "payload": {"user_id": user_id, "external_ref": "sub_abc"},
            },
        )
        assert webhook.status_code == 200
        assert webhook.json() == {"processed": True, "duplicate": False}

    async def test_duplicate_webhook_is_a_noop(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        """The idempotency gate: the same event id must apply exactly once."""
        user_id = await self._register(fresh_client)
        body = {
            "provider": "mock",
            "event_id": "evt-dup",
            "event_type": "subscription.created",
            "signature": "mock-signature",
            "payload": {"user_id": user_id},
        }
        first = await fresh_client.post("/api/v1/billing/webhook", json=body)
        second = await fresh_client.post("/api/v1/billing/webhook", json=body)
        assert first.json()["duplicate"] is False
        assert second.json()["duplicate"] is True
        assert second.status_code == 200  # providers retry; 200 with duplicate=True

    async def test_invalid_signature_rejected(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        webhook = await fresh_client.post(
            "/api/v1/billing/webhook",
            json={
                "provider": "mock",
                "event_id": "evt-bad",
                "event_type": "subscription.created",
                "signature": "forged",
                "payload": {"user_id": str(uuid.uuid4())},
            },
        )
        assert webhook.status_code == 401

    async def test_state_machine_rejects_illegal_transition(self) -> None:
        """active -> active is illegal; the machine must refuse, not drift."""
        from travel_planner.services.payments import PaymentError, transition

        assert transition("incomplete", "active") == "active"
        assert transition("active", "canceled") == "canceled"
        with pytest.raises(PaymentError):
            transition("active", "active")
        with pytest.raises(PaymentError):
            transition("canceled", "active")


class TestAffiliate:
    async def test_click_recorded_with_disclosure(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        response = await fresh_client.post(
            "/api/v1/affiliate/click",
            json={
                "category": "hotels",
                "target_url": "https://example-hotel.test/booking?room=deluxe",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sponsored"] in (True, False)
        assert "disclosure" in body
        assert "commission" in body["disclosure"]


class TestAdmin:
    async def test_admin_stats_require_admin_role(
        self, fresh_client: httpx.AsyncClient
    ) -> None:
        # Anonymous caller -> 401.
        anonymous = await fresh_client.get("/api/v1/admin/stats")
        assert anonymous.status_code == 401

        # Regular account -> 403.
        register = await fresh_client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "correct-horse-battery"},
        )
        token = register.json()["access_token"]
        forbidden = await fresh_client.get(
            "/api/v1/admin/stats", headers=_auth_header(token)
        )
        assert forbidden.status_code == 403

    async def test_bootstrap_admin_sees_stats(self) -> None:
        """ADMIN_BOOTSTRAP_EMAIL grants the admin role to the first account."""
        import os
        import uuid as _uuid
        from pathlib import Path

        from asgi_lifespan import LifespanManager

        from travel_planner.api.app import create_app

        folder = Path(".pytest_tmp")
        folder.mkdir(exist_ok=True)
        db = f"sqlite+aiosqlite:///{folder / ('admin' + _uuid.uuid4().hex[:6] + '.db')}"
        os.environ["ADMIN_BOOTSTRAP_EMAIL"] = "owner@example.com"
        # Settings are cached; force a reload so the bootstrap email is seen.
        from travel_planner.config.settings import reload_settings

        reload_settings()
        try:
            app = create_app(database_url=db)
            async with LifespanManager(app) as manager:
                transport = httpx.ASGITransport(app=manager.app)
                async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
                    register = await http.post(
                        "/api/v1/auth/register",
                        json={
                            "email": "owner@example.com",
                            "password": "correct-horse-battery",
                        },
                    )
                    assert register.json()["is_admin"] is True
                    token = register.json()["access_token"]

                    await http.post("/api/v1/trips", json={"request": "Shiraz weekend"})
                    stats = await http.get(
                        "/api/v1/admin/stats", headers=_auth_header(token)
                    )
                    assert stats.status_code == 200
                    body = stats.json()
                    assert body["users"] == 1
                    assert body["trips"] == 1
                    assert body["plans"] == 1
        finally:
            os.environ.pop("ADMIN_BOOTSTRAP_EMAIL", None)
            reload_settings()  # never leak the bootstrap email into other tests
