"""Payments: a provider protocol, adapters, and a subscription state machine.

Rules (ADR-007 and the master prompt):

* The agent never books or pays. Payments here are **subscriptions**, and even
  those only ever run in provider test mode in this codebase.
* No card data is ever stored or logged - only provider references.
* The Iran-compatible gateway (Zarinpal) sits behind a feature flag and has a
  disabled stub until credentials exist; the Stripe adapter has the same shape.
* Webhooks must be idempotent: ``WebhookEvent(provider, event_id)`` has a unique
  constraint and a duplicate delivery is a no-op.
"""

from __future__ import annotations

import logging
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.config.settings import Settings, get_settings
from travel_planner.db.models import Subscription, WebhookEvent

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """A payment-flow failure safe to surface to the caller."""


#: The subscription state machine: only these transitions are legal.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "incomplete": frozenset({"active", "canceled"}),
    "active": frozenset({"past_due", "canceled"}),
    "past_due": frozenset({"active", "canceled"}),
    "canceled": frozenset({"incomplete"}),
}


class PaymentProvider(Protocol):
    """Every payment adapter implements this - mock, Stripe, Zarinpal alike."""

    name: str

    def create_checkout(self, *, user_id: str, plan: str) -> dict[str, object]:
        ...

    def verify_webhook(self, *, payload: dict[str, object], signature: str) -> bool:
        ...


class MockPaymentProvider:
    """The default: deterministic, offline, used by tests and demo mode."""

    name = "mock"

    def create_checkout(self, *, user_id: str, plan: str) -> dict[str, object]:
        return {
            "provider": self.name,
            "checkout_url": f"/api/v1/billing/mock-checkout?plan={plan}",
            "user_id": user_id,
            "plan": plan,
            "mode": "test",
        }

    def verify_webhook(self, *, payload: dict[str, object], signature: str) -> bool:
        # The mock provider signs with a shared secret; tests use it explicitly.
        return signature == "mock-signature"


class StripePaymentProvider:
    """The international adapter. Requires ``STRIPE_SECRET_KEY`` to enable."""

    name = "stripe"

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self._secret = cfg.stripe_secret_key.get_secret_value().strip()
        self._webhook_secret = cfg.stripe_webhook_secret.get_secret_value().strip()

    @property
    def enabled(self) -> bool:
        return bool(self._secret)

    def create_checkout(self, *, user_id: str, plan: str) -> dict[str, object]:
        if not self.enabled:
            msg = "Stripe is not configured (missing STRIPE_SECRET_KEY)"
            raise PaymentError(msg)
        # A real integration calls Stripe's Checkout Session API here; the
        # shape is fixed so the call drops in without touching callers.
        return {
            "provider": self.name,
            "checkout_url": "https://checkout.stripe.com/... (test mode)",
            "user_id": user_id,
            "plan": plan,
            "mode": "test",
        }

    def verify_webhook(self, *, payload: dict[str, object], signature: str) -> bool:
        # Production computes HMAC-SHA256 over the raw body with the webhook
        # secret; implemented when credentials exist. Without a secret, reject.
        return bool(self._webhook_secret) and bool(signature)


class ZarinpalPaymentProvider:
    """The Iran-compatible adapter, behind ``ENABLE_IRAN_GATEWAY`` (ADR-007)."""

    name = "zarinpal"

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self._merchant_id = cfg.zarinpal_merchant_id.strip()
        self._sandbox = cfg.zarinpal_sandbox

    @property
    def enabled(self) -> bool:
        return bool(self._merchant_id)

    def create_checkout(self, *, user_id: str, plan: str) -> dict[str, object]:
        if not self.enabled:
            msg = "Zarinpal is not configured (missing ZARINPAL_MERCHANT_ID)"
            raise PaymentError(msg)
        return {
            "provider": self.name,
            "checkout_url": "https://sandbox.zarinpal.com/pg/StartPay/... (test)",
            "user_id": user_id,
            "plan": plan,
            "mode": "sandbox" if self._sandbox else "live",
        }

    def verify_webhook(self, *, payload: dict[str, object], signature: str) -> bool:
        return bool(self._merchant_id) and bool(signature)


def get_payment_provider(settings: Settings | None = None) -> PaymentProvider:
    """Resolve the configured provider; disabled adapters raise on use."""
    cfg = settings or get_settings()
    configured = cfg.payment_provider.strip().lower()
    if configured == "stripe":
        return StripePaymentProvider(cfg)
    if configured == "zarinpal":
        return ZarinpalPaymentProvider(cfg)
    return MockPaymentProvider()


# -------------------------------------------------------- subscription logic
def transition(current: str, target: str) -> str:
    """Apply the subscription state machine or raise PaymentError."""
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset({"incomplete", "active"}))
    if target not in allowed:
        msg = f"illegal subscription transition {current!r} -> {target!r}"
        raise PaymentError(msg)
    return target


async def ensure_subscription(
    session: AsyncSession, *, user_id: str | None, plan: str = "free"
) -> Subscription:
    """Fetch or create the caller's subscription row.

    New rows start as ``incomplete`` so the webhook state machine can drive
    them to ``active`` - creating them as active would make the first
    ``subscription.created`` event an illegal transition.
    """
    existing = (
        await session.execute(select(Subscription).where(Subscription.user_id == user_id))
    ).scalars().first()
    if existing is not None:
        return existing
    subscription = Subscription(
        user_id=user_id, plan=plan, provider="mock", status="incomplete"
    )
    session.add(subscription)
    await session.flush()
    return subscription


async def process_webhook(
    session: AsyncSession,
    *,
    provider: str,
    event_id: str,
    event_type: str,
    payload: dict[str, object],
) -> bool:
    """Apply a webhook exactly once. Returns False for duplicates.

    The event id is inserted under a unique constraint; a duplicate raises
    IntegrityError and is swallowed as a no-op - the caller still gets 200
    because providers retry until they see success.
    """
    duplicate = await session.execute(
        select(WebhookEvent.id).where(
            WebhookEvent.provider == provider, WebhookEvent.event_id == event_id
        )
    )
    if duplicate.scalars().first() is not None:
        logger.info("duplicate webhook %s/%s ignored", provider, event_id)
        return False

    from sqlalchemy.exc import IntegrityError

    session.add(
        WebhookEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        logger.info("concurrent duplicate webhook %s/%s ignored", provider, event_id)
        return False

    # Subscription state transitions driven by the event type.
    if event_type in {"subscription.created", "invoice.paid", "subscription.resumed"}:
        await _set_status(session, payload, "active", provider)
    elif event_type in {"subscription.past_due", "invoice.failed"}:
        await _set_status(session, payload, "past_due", provider)
    elif event_type == "subscription.canceled":
        await _set_status(session, payload, "canceled", provider)
    else:
        logger.info("webhook %s recorded without a state change", event_type)
    return True


async def _set_status(
    session: AsyncSession, payload: dict[str, object], target: str, provider: str
) -> None:
    """Move the referenced user's subscription to ``target`` (state machine)."""
    import uuid as _uuid

    user_ref = payload.get("user_id")
    if not isinstance(user_ref, str) or not user_ref:
        logger.warning("webhook without user_id; state change skipped")
        return
    try:
        user_id = _uuid.UUID(user_ref)
    except ValueError:
        logger.warning("webhook user_id %r is not a uuid", user_ref)
        return

    subscription = (
        await session.execute(select(Subscription).where(Subscription.user_id == user_id))
    ).scalars().first()
    if subscription is None:
        subscription = Subscription(
            user_id=user_id, plan="pro", provider=provider, status="incomplete"
        )
        session.add(subscription)
        await session.flush()

    subscription.status = transition(subscription.status, target)
    subscription.provider = provider
    external = payload.get("external_ref")
    subscription.external_ref = str(external) if external is not None else ""
    await session.flush()
    logger.info("subscription for %s -> %s", user_ref, target)

