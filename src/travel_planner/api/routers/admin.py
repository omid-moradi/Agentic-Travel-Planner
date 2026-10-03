"""Admin endpoints - protected by the admin role (STATUS-P6 scope: stats)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.app import error_response
from travel_planner.api.routers.auth import current_user
from travel_planner.api.routers.trips import db_session
from travel_planner.db.models import Itinerary, Trip, UsageEvent, User
from travel_planner.services import auth

router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
async def admin_stats(
    request: Request,
    user: object = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> object:
    """Users, trips, plans and token usage - the admin funnel basics."""
    caller = user
    if caller is None:
        return error_response(
            401, "unauthenticated", "Admin endpoints need a bearer token.", request.state.request_id
        )
    try:
        await auth.require_admin(session, str(caller.id))  # type: ignore[attr-defined]
    except auth.AuthError as exc:
        return error_response(403, "forbidden", str(exc), request.state.request_id)

    users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    trips = (await session.execute(select(func.count(Trip.id)))).scalar() or 0
    plans = (
        await session.execute(select(func.count(UsageEvent.id)).where(UsageEvent.kind == "plan"))
    ).scalar() or 0
    tokens = (await session.execute(select(func.coalesce(func.sum(UsageEvent.tokens), 0)))).scalar() or 0
    valid_itineraries = (
        await session.execute(select(func.count(Itinerary.id)).where(Itinerary.is_valid.is_(True)))
    ).scalar() or 0

    return {
        "users": int(users),
        "trips": int(trips),
        "plans": int(plans),
        "valid_itineraries": int(valid_itineraries),
        "tokens_used": int(tokens),
    }
