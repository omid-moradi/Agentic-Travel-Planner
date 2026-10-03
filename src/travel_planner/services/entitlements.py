"""Entitlements: plan tiers, quotas and usage metering.

Every metered action goes through :class:`EntitlementService` before it runs -
the API layer never decides quotas on its own. Quotas count ``usage_events``
rows in the current calendar month, so enforcement needs no extra tables.

Guests (no account) get the master prompt's guest trial: one free plan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.config.settings import Settings, get_settings
from travel_planner.db.models import UsageEvent

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """The caller hit a plan limit. The message is safe to show the user."""

    def __init__(self, message: str, *, plan: str, limit: int, used: int) -> None:
        super().__init__(message)
        self.plan = plan
        self.limit = limit
        self.used = used


@dataclass(frozen=True, slots=True)
class PlanLimits:
    plan: str
    plans_per_month: int
    replans_per_month: int
    max_tokens_per_plan: int


class EntitlementService:
    """Central quota check + usage metering for one configured system."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def limits_for(self, plan: str) -> PlanLimits:
        free = self._settings.free_tier_plans_per_month
        pro = self._settings.pro_tier_plans_per_month
        table = {
            "guest": PlanLimits("guest", 1, 0, 4_096),
            "free": PlanLimits("free", free, max(1, free // 3), 100_000),
            "pro": PlanLimits("pro", pro, max(3, pro // 5), 1_000_000),
            "team": PlanLimits("team", 1_000, 500, 10_000_000),
        }
        if plan == "guest" and not self._settings.guest_trial_enabled:
            # Deployments without the guest trial treat anonymous callers
            # like the free tier (a development/internal switch).
            return table["free"]
        return table.get(plan, table["free"])

    async def usage_this_month(
        self, session: AsyncSession, *, user_id: str | None, kind: str
    ) -> int:
        """Count usage events of ``kind`` for the caller in the current month."""
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        statement = (
            select(func.count(UsageEvent.id))
            .where(UsageEvent.kind == kind)
            .where(UsageEvent.created_at >= start)
        )
        if user_id:
            import uuid as _uuid

            from travel_planner.db.models import Trip

            try:
                parsed_user = _uuid.UUID(user_id)
            except ValueError:
                return 0  # a malformed subject matches nothing
            # Usage rows carry trip_id; join to the caller's trips.
            trip_ids = select(Trip.id).where(Trip.user_id == parsed_user)
            statement = statement.where(UsageEvent.trip_id.in_(trip_ids))
        result = await session.execute(statement)
        return int(result.scalar() or 0)

    async def check_quota(
        self,
        session: AsyncSession,
        *,
        user_id: str | None,
        plan: str,
        kind: str,
        limit: int,
    ) -> None:
        """Raise :class:`QuotaExceededError` when the monthly limit is hit."""
        used = await self.usage_this_month(session, user_id=user_id, kind=kind)
        if used >= limit:
            msg = (
                f"Plan limit reached: {limit} {kind} per month on the {plan} plan. "
                "Upgrade or wait for the next cycle."
            )
            raise QuotaExceededError(msg, plan=plan, limit=limit, used=used)

    async def record_usage(
        self,
        session: AsyncSession,
        *,
        user_id: str | None,
        trip_id: object | None = None,
        kind: str,
        tokens: int = 0,
        tool_calls: int = 0,
        estimated_cost: float = 0.0,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Persist one metered action (never called on the failure path)."""
        from travel_planner.db.models import UsageEvent

        session.add(
            UsageEvent(
                user_id=None,  # linked through the trip; see usage_this_month
                trip_id=trip_id,
                kind=kind,
                tokens=tokens,
                tool_calls=tool_calls,
                estimated_cost=estimated_cost,
                metadata_=metadata or {},
            )
        )
        await session.flush()

