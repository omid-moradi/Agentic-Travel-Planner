"""Share link endpoints - public read-only trip pages."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.app import error_response
from travel_planner.api.routers.trips import db_session
from travel_planner.db.models import ShareLink
from travel_planner.services import trips as service

router = APIRouter(tags=["share"])


@router.post("/trips/{trip_id}/share", status_code=201)
async def create_share_link(
    trip_id: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    """Create (or return) an active share token for a trip."""
    try:
        parsed = uuid.UUID(trip_id)
    except ValueError:
        return error_response(400, "invalid_id", "trip_id must be a UUID", request.state.request_id)

    trip = await service.get_trip(session, parsed)
    if trip is None:
        return error_response(404, "not_found", f"trip {trip_id} does not exist", request.state.request_id)

    existing = (
        await session.execute(
            select(ShareLink)
            .where(ShareLink.trip_id == parsed, ShareLink.is_active.is_(True))
            .limit(1)
        )
    ).scalars().first()
    if existing is not None:
        return {"trip_id": trip_id, "token": existing.token, "share_url": f"/api/v1/share/{existing.token}"}

    link = ShareLink(trip_id=parsed)
    session.add(link)
    await session.commit()
    return {"trip_id": trip_id, "token": link.token, "share_url": f"/api/v1/share/{link.token}"}


@router.get("/share/{token}")
async def get_shared_trip(
    token: str, request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    """The public, read-only view of a trip. No itinerary edits are possible here."""
    link = (
        await session.execute(select(ShareLink).where(ShareLink.token == token).limit(1))
    ).scalars().first()
    if link is None or not link.is_active:
        return error_response(404, "not_found", "share link does not exist", request.state.request_id)

    trip = await service.get_trip(session, link.trip_id)
    if trip is None:  # pragma: no cover - defensive
        return error_response(404, "not_found", "trip missing", request.state.request_id)

    itinerary = await service.latest_itinerary(session, link.trip_id)
    return {
        "trip": {
            "title": trip.title,
            "region": trip.region,
            "language": trip.language,
            "start_date": str(trip.start_date) if trip.start_date else None,
            "duration_nights": trip.duration_nights,
        },
        "itinerary": (
            {
                "version": itinerary.version,
                "is_valid": itinerary.is_valid,
                "total_cost": itinerary.total_cost,
                "currency": itinerary.currency,
                "payload": itinerary.payload,
            }
            if itinerary
            else None
        ),
        "read_only": True,
    }
