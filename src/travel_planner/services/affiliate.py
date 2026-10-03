"""Affiliate links: redirect only, click tracking, honest disclosure (ADR-007).

The agent never books or pays. This service builds a provider link with an
affiliate id from env, records the click, and returns the URL for the client
to open. The response always carries ``sponsored: true`` so the UI must show
the disclosure - it cannot be hidden by a caller.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.config.settings import Settings, get_settings
from travel_planner.db.models import AffiliateClick

logger = logging.getLogger(__name__)

#: env affiliate id per category.
_CATEGORY_ENV = {
    "hotels": "affiliate_hotels_id",
    "flights": "affiliate_flights_id",
    "activities": "affiliate_activities_id",
}


def build_affiliate_url(
    target_url: str, category: str, *, settings: Settings | None = None
) -> tuple[str, bool]:
    """Return (url, sponsored). Without an affiliate id the URL is unchanged.

    The param name is deliberately provider-neutral; a real provider adapter
    maps it to their tag format in a later phase.
    """
    cfg = settings or get_settings()
    affiliate_id = getattr(cfg, _CATEGORY_ENV.get(category, ""), "")
    if not affiliate_id:
        return target_url, False
    separator = "&" if "?" in target_url else "?"
    return f"{target_url}{separator}{urlencode({'aff': affiliate_id})}", True


async def record_click(
    session: AsyncSession,
    *,
    trip_id: str | None,
    category: str,
    target_url: str,
    sponsored: bool,
) -> AffiliateClick:
    """Persist one affiliate click for the funnel and the payout audit."""
    import uuid as _uuid

    click = AffiliateClick(
        trip_id=_uuid.UUID(trip_id) if trip_id else None,
        category=category,
        target_url=target_url,
        affiliate_id="env-configured" if sponsored else "",
    )
    session.add(click)
    await session.flush()
    return click
