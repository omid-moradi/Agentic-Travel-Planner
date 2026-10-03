"""Trips endpoints: create, get, list, messages, replan, trace, itinerary."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date as date_type

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.app import error_response
from travel_planner.db.models import Trip
from travel_planner.db.session import get_sessionmaker, resolve_database_url
from travel_planner.services import trips as service

router = APIRouter(tags=["trips"])


async def db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Open a session bound to the app's configured database URL."""
    url = request.app.state.database_url or resolve_database_url()
    maker = get_sessionmaker(url)
    async with maker() as session:
        yield session


def _parse_trip_id(trip_id: str, request: Request) -> uuid.UUID | object:
    """Parse a trip id or return the error envelope."""
    try:
        return uuid.UUID(trip_id)
    except ValueError:
        return error_response(
            400, "invalid_id", "trip_id must be a UUID", request.state.request_id
        )


def _bearer_credentials(request: Request) -> str | None:
    """Extract the bearer token from the Authorization header, if any."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


class CreateTripRequest(BaseModel):
    """Typed request body for POST /trips."""

    request: str = Field(min_length=3, max_length=4000, description="Trip request")
    region: str = Field(default="iran", pattern="^(iran|international)$")
    language: str = Field(default="fa", pattern="^(fa|en)$")
    start_date: date_type | None = None
    duration_nights: int = Field(default=3, ge=1, le=90)
    travelers: int = Field(default=1, ge=1, le=50)
    budget_total: float | None = Field(default=None, ge=0)
    budget_currency: str | None = None


class TripResponse(BaseModel):
    id: str
    title: str
    status: str
    region: str
    language: str
    start_date: date_type | None
    duration_nights: int
    travelers: int
    created_at: str


def _trip_response(trip: Trip) -> TripResponse:
    return TripResponse(
        id=str(trip.id),
        title=trip.title,
        status=trip.status,
        region=trip.region,
        language=trip.language,
        start_date=trip.start_date,
        duration_nights=trip.duration_nights,
        travelers=trip.travelers,
        created_at=str(trip.created_at),
    )


@router.post("/trips", status_code=201)
async def create_trip(
    body: CreateTripRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
    caller: object | None = None,
) -> object:
    """Create a trip and plan it immediately (offline demo graph in this phase).

    Quota check first: guests get one plan (the guest trial), accounts get
    their plan's monthly limit. Rejected callers get the quota error envelope.
    """
    # Resolve the caller from the bearer token (optional auth).
    from travel_planner.services.entitlements import EntitlementService, QuotaExceededError

    user = None
    # Reuse the bearer scheme without a second dependency declaration.
    credentials = _bearer_credentials(request)
    if credentials is not None:
        from travel_planner.services import auth as auth_service

        try:
            user = await auth_service.get_user(session, auth_service.decode_access_token(credentials))
        except auth_service.AuthError:
            user = None

    plan = "free" if user is not None else "guest"
    entitlements = EntitlementService()
    limits = entitlements.limits_for(plan)
    try:
        await entitlements.check_quota(
            session, user_id=str(user.id) if user else None, plan=plan,
            kind="plan", limit=limits.plans_per_month,
        )
    except QuotaExceededError as exc:
        return error_response(
            402,
            "quota_exceeded",
            str(exc),
            request.state.request_id,
            details={"plan": exc.plan, "limit": exc.limit, "used": exc.used},
        )

    trip = await service.create_trip(
        session,
        raw_request=body.request,
        region=body.region,
        language=body.language,
        start_date=body.start_date,
        duration_nights=body.duration_nights,
        travelers=body.travelers,
        budget_total=body.budget_total,
        budget_currency=body.budget_currency,
        user_id=getattr(user, "id", None),
    )
    # The graph is deterministic and fast offline; run it inline for now.
    trip = await service.run_plan_for_trip(session, trip)
    await session.commit()
    return _trip_response(trip)


@router.get("/trips")
async def list_trips(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(db_session),
) -> object:
    rows = await service.list_trips(session, limit=min(limit, 200), offset=offset)
    return {"items": [_trip_response(t) for t in rows], "count": len(rows)}


@router.get("/trips/{trip_id}")
async def get_trip(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if isinstance(parsed, uuid.UUID):
        trip = await service.get_trip(session, parsed)
        if trip is not None:
            return _trip_response(trip)
        return error_response(
            404, "not_found", f"trip {trip_id} does not exist", request.state.request_id
        )
    return parsed


@router.get("/trips/{trip_id}/itinerary")
async def get_itinerary(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(
            404, "not_found", f"trip {trip_id} does not exist", request.state.request_id
        )
    itinerary = await service.latest_itinerary(session, parsed)
    if itinerary is None:
        return error_response(
            404, "no_itinerary", "this trip has no itinerary yet", request.state.request_id
        )
    return {
        "trip_id": trip_id,
        "version": itinerary.version,
        "is_valid": itinerary.is_valid,
        "total_cost": itinerary.total_cost,
        "currency": itinerary.currency,
        "payload": itinerary.payload,
    }


@router.get("/trips/{trip_id}/messages")
async def get_messages(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    rows = await service.list_messages(session, parsed)
    return {
        "items": [
            {
                "role": m.role,
                "content": m.content,
                "kind": m.kind,
                "created_at": str(m.created_at),
            }
            for m in rows
        ]
    }


@router.get("/trips/{trip_id}/trace")
async def get_trace(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    """The agent trace: structured steps and timings, never chain-of-thought."""
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    runs = await service.list_agent_runs(session, parsed)
    return {
        "items": [
            {
                "node": run.node,
                "status": run.status,
                "tokens": run.tokens,
                "duration_ms": run.duration_ms,
                "payload": run.payload,
                "created_at": str(run.created_at),
            }
            for run in runs
        ]
    }


@router.post("/trips/{trip_id}/replan")
async def replan(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    """Re-run the plan; the previous version is kept as history."""
    parsed = _parse_trip_id(trip_id, request)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(
            404, "not_found", f"trip {trip_id} does not exist", request.state.request_id
        )
    trip = await service.run_plan_for_trip(session, trip)
    await session.commit()
    return _trip_response(trip)
