"""Whole-trip feature tests - the phase 7 gate.

Covers the checklists (packing + documents), advisory entry requirements,
the expense tracker with currency conversion and burn-down, the ICS and PDF
exports (the gate), and Live Mode (today's plan + one-tap re-plan).

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
async def client() -> httpx.AsyncClient:
    """A fresh app + database; quotas are relaxed to keep the focus here."""
    import os

    from asgi_lifespan import LifespanManager

    from travel_planner.api.app import create_app
    from travel_planner.config.settings import reload_settings

    os.environ["FREE_TIER_PLANS_PER_MONTH"] = "1000"
    os.environ["GUEST_TRIAL_ENABLED"] = "false"
    reload_settings()
    try:
        app = create_app(database_url=_temp_db("wholetrip"))
        async with LifespanManager(app) as manager:
            transport = httpx.ASGITransport(app=manager.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
                yield http
    finally:
        os.environ.pop("FREE_TIER_PLANS_PER_MONTH", None)
        os.environ.pop("GUEST_TRIAL_ENABLED", None)
        reload_settings()


async def _create_trip(client: httpx.AsyncClient, **overrides: object) -> str:
    payload: dict[str, object] = {"request": "Tehran to Shiraz, 3 nights"}
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


class TestChecklists:
    async def test_packing_list_generated(self, client: httpx.AsyncClient) -> None:
        trip_id = await _create_trip(client)
        checklist = await client.get(f"/api/v1/trips/{trip_id}/checklist")
        assert checklist.status_code == 200
        body = checklist.json()
        assert len(body["packing"]) >= 5
        assert all(item["reason"] for item in body["packing"])

    async def test_iran_documents_warning_present(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client, region="iran")
        checklist = await client.get(f"/api/v1/trips/{trip_id}/checklist")
        documents = checklist.json()["documents"]
        # The verify-with-official-source warning is mandatory, never dropped.
        assert "official" in documents["warning"]
        ids = [doc["id"] for doc in documents["documents"]]
        assert "national-id" in ids

    async def test_international_documents_list_passport(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client, region="international")
        checklist = await client.get(f"/api/v1/trips/{trip_id}/checklist")
        ids = [doc["id"] for doc in checklist.json()["documents"]["documents"]]
        assert "passport" in ids
        assert "visa" in ids


class TestEntryRequirements:
    async def test_international_requirements_are_advisory(
        self, client: httpx.AsyncClient
    ) -> None:
        """ADR-009: never state visa rules as certain without a source."""
        trip_id = await _create_trip(client, region="international")
        requirements = await client.get(
            f"/api/v1/trips/{trip_id}/entry-requirements"
        )
        assert requirements.status_code == 200
        body = requirements.json()
        assert body["status"] == "inferred"
        assert all(item["status"] == "inferred" for item in body["items"])
        assert "official" in body["warning"]

    async def test_domestic_requirements_are_simple(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client, region="iran")
        requirements = await client.get(
            f"/api/v1/trips/{trip_id}/entry-requirements"
        )
        items = requirements.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "confirmed"


class TestExpenses:
    async def test_add_and_burn_down(self, client: httpx.AsyncClient) -> None:
        trip_id = await _create_trip(client)

        first = await client.post(
            f"/api/v1/trips/{trip_id}/expenses",
            json={"title": "Lunch", "amount": 250_000, "currency": "TOMAN", "category": "food"},
        )
        assert first.status_code == 201, first.text
        assert first.json()["amount_in_trip_currency"] == 250_000

        # A USD expense is converted at the documented static rate.
        second = await client.post(
            f"/api/v1/trips/{trip_id}/expenses",
            json={"title": "Museum ticket", "amount": 5, "currency": "USD", "category": "ticket"},
        )
        assert second.status_code == 201
        assert second.json()["amount_in_trip_currency"] == 5 * 100_000

        summary = await client.get(f"/api/v1/trips/{trip_id}/expenses")
        assert summary.status_code == 200
        burn = summary.json()["burn_down"]
        assert burn["spent"] == 250_000 + 500_000
        assert burn["by_category"]["food"] == 250_000
        assert burn["by_category"]["ticket"] == 500_000
        # Burn-down compares against the itinerary's estimated total.
        assert burn["budget"] is not None
        assert burn["remaining"] == burn["budget"] - burn["spent"]

    async def test_unknown_currency_rejected(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client)
        bad = await client.post(
            f"/api/v1/trips/{trip_id}/expenses",
            json={"title": "Mystery", "amount": 10, "currency": "XYZ", "category": "other"},
        )
        assert bad.status_code == 400
        assert bad.json()["error"]["code"] == "invalid_expense"


class TestExports:
    """The phase 7 gate: ICS and PDF exports."""

    async def test_ics_is_valid_rfc5545(self, client: httpx.AsyncClient) -> None:
        trip_id = await _create_trip(client)
        export = await client.get(f"/api/v1/trips/{trip_id}/export.ics")
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/calendar")
        assert "attachment" in export.headers["content-disposition"]

        text = export.text
        assert text.startswith("BEGIN:VCALENDAR")
        assert text.rstrip("\r\n").endswith("END:VCALENDAR")
        # One VEVENT per day (3 nights -> 3 days).
        assert text.count("BEGIN:VEVENT") == 3
        # All-day date values and the summary carry the city.
        assert "DTSTART;VALUE=DATE:" in text
        assert "Tehran" in text or "Shiraz" in text
        # RFC 5545 requires CRLF line endings.
        assert "\r\n" in text

    async def test_pdf_is_a_valid_pdf(self, client: httpx.AsyncClient) -> None:
        trip_id = await _create_trip(client)
        export = await client.get(f"/api/v1/trips/{trip_id}/export.pdf")
        assert export.status_code == 200
        assert export.headers["content-type"] == "application/pdf"

        content = export.content
        # Header, xref table and EOF - the three things every reader checks.
        assert content.startswith(b"%PDF-1.4")
        assert b"xref" in content
        assert content.rstrip().endswith(b"%%EOF")
        # One page, one font, five indirect objects.
        assert b"/Type /Catalog" in content
        assert b"/Count 1" in content
        assert content.count(b" 0 obj\n") == 5

    async def test_export_without_itinerary_404s(
        self, client: httpx.AsyncClient
    ) -> None:
        unknown = uuid.uuid4()
        ics = await client.get(f"/api/v1/trips/{unknown}/export.ics")
        pdf = await client.get(f"/api/v1/trips/{unknown}/export.pdf")
        assert ics.status_code == 404
        assert pdf.status_code == 404


class TestLiveMode:
    async def test_today_returns_plan_and_reasons(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client, start_date="2026-12-01")
        today = await client.get(f"/api/v1/trips/{trip_id}/today")
        assert today.status_code == 200
        body = today.json()
        # The plan resolves to a day with activities (today or the next day).
        assert body["plan"]["day"] is not None
        assert len(body["plan"]["day"]["activities"]) >= 2
        # All five one-tap re-plan reasons are offered.
        reasons = {r["reason"] for r in body["replan_reasons"]}
        assert reasons == {"rain", "closed_venue", "running_late", "tired", "budget_changed"}

    async def test_replan_today_records_the_reason(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client)
        replan = await client.post(
            f"/api/v1/trips/{trip_id}/replan-today", json={"reason": "rain"}
        )
        assert replan.status_code == 200
        assert replan.json() == {
            "replanned": True,
            "reason": "rain",
            "trip_status": "done",
        }

        # The reason is auditable on the trace.
        trace = await client.get(f"/api/v1/trips/{trip_id}/trace")
        rain_run = next(
            run for run in trace.json()["items"] if run["node"] == "replan_today"
        )
        assert rain_run["payload"]["reason"] == "rain"

    async def test_unknown_replan_reason_rejected(
        self, client: httpx.AsyncClient
    ) -> None:
        trip_id = await _create_trip(client)
        replan = await client.post(
            f"/api/v1/trips/{trip_id}/replan-today", json={"reason": "boredom"}
        )
        assert replan.status_code == 400
        assert replan.json()["error"]["code"] == "invalid_reason"
