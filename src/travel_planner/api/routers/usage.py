"""Usage and entitlement endpoints (quota enforcement arrives in phase 6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.routers.trips import db_session
from travel_planner.config.settings import get_settings
from travel_planner.db.models import UsageEvent

router = APIRouter(tags=["usage"])


@router.get("/usage")
async def usage(
    request: Request, session: AsyncSession = Depends(db_session)
) -> object:
    """Aggregated usage for the caller (anonymous until auth exists)."""
    result = await session.execute(
        select(
            UsageEvent.kind,
            func.count(UsageEvent.id),
            func.coalesce(func.sum(UsageEvent.tokens), 0),
        ).group_by(UsageEvent.kind)
    )
    rows = result.all()
    settings = get_settings()
    return {
        "items": [
            {"kind": kind, "count": count, "tokens": tokens}
            for kind, count, tokens in rows
        ],
        # Quotas are shown but only enforced from phase 6.
        "quotas": {
            "free_plans_per_month": settings.free_tier_plans_per_month,
            "pro_plans_per_month": settings.pro_tier_plans_per_month,
        },
    }
