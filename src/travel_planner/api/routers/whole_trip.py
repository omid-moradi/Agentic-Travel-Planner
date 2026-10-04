"""Whole-trip endpoints: checklists, entry requirements, expenses, exports, live mode."""

from __future__ import annotations

import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.app import error_response
from travel_planner.api.routers.trips import _parse_trip_id, db_session
from travel_planner.db.models import ItineraryDay
from travel_planner.schemas import Itinerary
from travel_planner.services import checklists, entry_requirements, expenses, exports
from travel_planner.services import live_mode as live
from travel_planner.services import trips as service

router = APIRouter(tags=["whole-trip"])


async def _load_itinerary(session: AsyncSession, trip_id: uuid.UUID) -> Itinerary | None:
    row = await service.latest_itinerary(session, trip_id)
    if row is None:
        return None
    return Itinerary.model_validate(row.payload)


# ------------------------------------------------------------------ checklist
@router.get("/trips/{trip_id}/checklist")
async def get_checklist(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(404, "not_found", f"trip {trip_id} does not exist", request.state.request_id)
    return {
        "packing": checklists.packing_list(trip),
        "documents": checklists.document_checklist(trip),
    }


# -------------------------------------------------------- entry requirements
@router.get("/trips/{trip_id}/entry-requirements")
async def get_entry_requirements(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(404, "not_found", f"trip {trip_id} does not exist", request.state.request_id)
    return entry_requirements.entry_requirements(trip)


# ------------------------------------------------------------------ expenses
class AddExpenseRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0)
    currency: str = Field(default="TOMAN", min_length=3, max_length=8)
    category: str = Field(default="other", pattern="^(food|transport|hotel|ticket|other)$")
    day_number: int | None = Field(default=None, ge=1, le=365)
    note: str = Field(default="", max_length=2000)


@router.post("/trips/{trip_id}/expenses", status_code=201)
async def add_expense(
    trip_id: str,
    body: AddExpenseRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(404, "not_found", f"trip {trip_id} does not exist", request.state.request_id)

    trip_currency = trip.budget_currency or "TOMAN"
    try:
        expense = await expenses.add_expense(
            session,
            trip_id=parsed,
            title=body.title,
            amount=body.amount,
            currency=body.currency,
            category=body.category,
            day_number=body.day_number,
            note=body.note,
            trip_currency=trip_currency,
        )
    except Exception as exc:  # unknown currency pair, etc.
        return error_response(400, "invalid_expense", str(exc), request.state.request_id)
    await session.commit()
    return {
        "id": str(expense.id),
        "title": expense.title,
        "amount": expense.amount,
        "currency": expense.currency,
        "amount_in_trip_currency": expense.amount_in_trip_currency,
    }


@router.get("/trips/{trip_id}/expenses")
async def get_expenses(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(404, "not_found", f"trip {trip_id} does not exist", request.state.request_id)

    rows = await expenses.list_expenses(session, parsed)
    itinerary = await service.latest_itinerary(session, parsed)
    burn = await expenses.burn_down(
        session,
        trip_id=parsed,
        estimated_total=itinerary.total_cost if itinerary else None,
        trip_currency=trip.budget_currency or "TOMAN",
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "title": row.title,
                "amount": row.amount,
                "currency": row.currency,
                "amount_in_trip_currency": row.amount_in_trip_currency,
                "category": row.category,
                "day_number": row.day_number,
                "created_at": str(row.created_at),
            }
            for row in rows
        ],
        "burn_down": {
            "spent": burn.spent,
            "budget": burn.budget,
            "remaining": burn.remaining,
            "currency": burn.currency,
            "by_category": burn.by_category,
            "status": burn.status,
        },
    }


# ------------------------------------------------------------------- exports
@router.get("/trips/{trip_id}/export.ics")
async def export_ics(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> Response:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return Response(content=str(parsed), status_code=400, media_type="application/json")
    trip = await service.get_trip(session, parsed)
    itinerary_model = await _load_itinerary(session, parsed)
    if trip is None or itinerary_model is None:
        return Response(content="not found", status_code=404)
    ics = exports.itinerary_to_ics(itinerary_model, title=trip.title or "Trip")
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="trip-{trip_id}.ics"'},
    )


@router.get("/trips/{trip_id}/export.pdf")
async def export_pdf(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> Response:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return Response(content=str(parsed), status_code=400, media_type="application/json")
    trip = await service.get_trip(session, parsed)
    itinerary_model = await _load_itinerary(session, parsed)
    if trip is None or itinerary_model is None:
        return Response(content="not found", status_code=404)
    pdf = exports.itinerary_to_pdf(itinerary_model, title=trip.title or "Trip")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="trip-{trip_id}.pdf"'},
    )


# ------------------------------------------------------------------ live mode
@router.get("/trips/{trip_id}/today")
async def today(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    """Today's plan with next-stop hints, plus the one-tap re-plan reasons."""
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    itinerary_model = await _load_itinerary(session, parsed)
    if itinerary_model is None:
        return error_response(
            404, "no_itinerary", "this trip has no itinerary yet", request.state.request_id
        )
    return {"plan": live.today_plan(itinerary_model), "replan_reasons": live.replan_reasons()}


@router.post("/trips/{trip_id}/replan-today")
async def replan_today(
    trip_id: str,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> object:
    """One-tap re-plan with a reason (Live Mode).

    The deterministic planner re-runs first (its trace is recorded), then
    the stored version is the merge: **today's day carries the reason-aware
    patch** (a lighter day when tired, no walking legs in the rain, a
    cheaper day on a budget change, ...) and **every other day keeps the
    plan the traveller already has**. When today is not a trip day the
    fresh full plan is stored unchanged (the pre-patch behaviour).
    """
    body: dict[str, object] = {}
    raw = await request.body()
    if raw:
        import json as _json

        body = _json.loads(raw)
    reason = str(body.get("reason", "tired"))
    if reason not in live.REASON_LABELS:
        return error_response(
            400, "invalid_reason", f"unknown reason {reason!r}", request.state.request_id
        )

    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(404, "not_found", f"trip {trip_id} does not exist", request.state.request_id)

    previous_itinerary = await _load_itinerary(session, parsed)
    trip = await service.run_plan_for_trip(session, trip)

    # Reason-aware, day-scoped patch on the freshly persisted version.
    day_patched = False
    fresh_row = await service.latest_itinerary(session, parsed)
    today = date_type.today()
    if (
        previous_itinerary is not None
        and fresh_row is not None
        and fresh_row.payload
        and any(d.date == today for d in previous_itinerary.days)
    ):
        fresh = Itinerary.model_validate(fresh_row.payload)
        merged = live.merge_patched_today(previous_itinerary, fresh, today, reason)  # type: ignore[arg-type]
        fresh_row.payload = merged.model_dump(mode="json")
        if merged.total_cost is not None:
            fresh_row.total_cost = merged.total_cost.amount
        patched_day = next(d for d in merged.days if d.date == today)
        result = await session.execute(
            select(ItineraryDay).where(
                ItineraryDay.itinerary_id == fresh_row.id,
                ItineraryDay.day_date == today,
            )
        )
        day_row = result.scalars().first()
        if day_row is not None:
            day_row.payload = patched_day.model_dump(mode="json")
            day_row.budget = (
                patched_day.daily_budget.amount if patched_day.daily_budget else None
            )
        day_patched = True

    # Record the live-mode reason on the trace so the edit is auditable.
    from travel_planner.db.models import AgentRun

    session.add(
        AgentRun(
            trip_id=parsed,
            node="replan_today",
            status="ok",
            payload={"reason": reason, "day_patched": day_patched},
        )
    )
    await session.commit()
    return {
        "replanned": True,
        "reason": reason,
        "day_patched": day_patched,
        "trip_status": trip.status,
    }

