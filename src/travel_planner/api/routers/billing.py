"""Billing endpoints: checkout, subscription status, idempotent webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.api.app import error_response
from travel_planner.api.routers.auth import current_user
from travel_planner.api.routers.trips import db_session
from travel_planner.config.settings import get_settings
from travel_planner.db.models import Subscription, User
from travel_planner.services import payments as pay
from travel_planner.services.entitlements import EntitlementService

router = APIRouter(tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(pro|team)$")


class WebhookBody(BaseModel):
    provider: str = Field(default="mock", pattern="^(mock|stripe|zarinpal)$")
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=64)
    signature: str = Field(default="", max_length=256)
    payload: dict[str, object] = Field(default_factory=dict)


@router.post("/billing/checkout")
async def checkout(
    body: CheckoutRequest,
    request: Request,
    user: User | None = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> object:
    """Create a provider checkout (test mode only; redirect, never a charge)."""
    if user is None:
        return error_response(
            401,
            "unauthenticated",
            "Create an account before subscribing.",
            request.state.request_id,
        )
    settings = get_settings()
    if not settings.billing_enabled:
        return error_response(
            503, "billing_disabled", "Billing is not enabled on this deployment.", request.state.request_id
        )
    provider = pay.get_payment_provider(settings)
    try:
        checkout_data = provider.create_checkout(user_id=str(user.id), plan=body.plan)
    except pay.PaymentError as exc:
        return error_response(503, "provider_unavailable", str(exc), request.state.request_id)
    await session.commit()
    return checkout_data


@router.get("/billing/status")
async def billing_status(
    request: Request,
    user: User | None = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> object:
    """The caller's subscription and the effective quota summary."""
    if user is None:
        # A guest has no subscription row; report the guest trial limits.
        entitlements = EntitlementService()
        limits = entitlements.limits_for("guest")
        return {
            "authenticated": False,
            "plan": "guest",
            "subscription_status": None,
            "limits": {
                "plans_per_month": limits.plans_per_month,
                "replans_per_month": limits.replans_per_month,
                "max_tokens_per_plan": limits.max_tokens_per_plan,
            },
        }

    subscription = (
        (
            await session.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
        )
        .scalars()
        .first()
    )
    entitlements = EntitlementService()
    plan = subscription.plan if subscription else "free"
    limits = entitlements.limits_for(plan)
    return {
        "authenticated": user is not None,
        "plan": plan,
        "subscription_status": subscription.status if subscription else None,
        "limits": {
            "plans_per_month": limits.plans_per_month,
            "replans_per_month": limits.replans_per_month,
            "max_tokens_per_plan": limits.max_tokens_per_plan,
        },
    }


@router.post("/billing/webhook")
async def billing_webhook(
    body: WebhookBody,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> object:
    """Receive a provider webhook. Idempotent by (provider, event_id).

    A duplicate delivery returns 200 with ``duplicate: true`` - providers
    retry until they see success and must not be punished for our bug.
    """
    settings = get_settings()
    provider_impl = pay.get_payment_provider(settings)
    if not provider_impl.verify_webhook(payload=body.payload, signature=body.signature):
        return error_response(
            401, "invalid_signature", "Webhook signature verification failed.", request.state.request_id
        )

    applied = await pay.process_webhook(
        session,
        provider=body.provider,
        event_id=body.event_id,
        event_type=body.event_type,
        payload=body.payload,
    )
    await session.commit()
    return {"processed": applied, "duplicate": not applied}
