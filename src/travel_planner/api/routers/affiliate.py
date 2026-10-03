"""Affiliate endpoints: build + record a redirect, always with disclosure."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.routers.trips import db_session
from travel_planner.services import affiliate as aff

router = APIRouter(tags=["affiliate"])


class AffiliateClickRequest(BaseModel):
    category: str = Field(pattern="^(hotels|flights|activities)$")
    target_url: str = Field(min_length=8, max_length=2000)
    trip_id: str | None = None


@router.post("/affiliate/click")
async def affiliate_click(
    body: AffiliateClickRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> object:
    """Record the click and return the redirect URL with its disclosure state.

    The agent never books or pays: the client opens the URL itself. The
    ``sponsored`` flag must be rendered in the UI (ADR-007).
    """
    url, sponsored = aff.build_affiliate_url(body.target_url, body.category)
    await aff.record_click(
        session, trip_id=body.trip_id, category=body.category, target_url=url, sponsored=sponsored
    )
    await session.commit()
    return {
        "redirect_url": url,
        "sponsored": sponsored,
        "disclosure": (
            "This link may earn us a commission. The provider's terms apply; "
            "the price is the same for you."
        ),
    }
