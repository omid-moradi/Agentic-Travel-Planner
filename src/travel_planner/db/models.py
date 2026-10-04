"""Database models - the full product schema (master prompt, section 6).

Design notes:

* ``users``/``subscriptions``/``usage_events`` exist from day one even though auth
  and billing arrive in phase 6 - renaming tables later is painful, while leaving
  them unused is free. All rows are created with a ``user_id = None`` anonymous
  user until accounts exist.
* Nested product data (itinerary payload, findings, trace) is stored as JSON.
  It is strongly typed at the Pydantic boundary; flattening every nesting level
  into tables would add joins without adding integrity.
* Times are UTC. Money keeps the Toman integers it was produced with.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    """Declarative base for every model."""


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ------------------------------------------------------------------- users
class User(IdMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    locale: Mapped[str] = mapped_column(String(8), default="fa")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Long-term preference memory: pace, food, transport, budget style.
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Subscription(IdMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    plan: Mapped[str] = mapped_column(String(16), default="free")
    status: Mapped[str] = mapped_column(String(16), default="active")
    provider: Mapped[str] = mapped_column(String(16), default="mock")
    external_ref: Mapped[str] = mapped_column(String(128), default="")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UsageEvent(IdMixin, Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_kind", "user_id", "kind"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trips.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

# ------------------------------------------------------------------- trips
class Trip(IdMixin, Base):
    __tablename__ = "trips"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    raw_request: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(16), default="iran")
    language: Mapped[str] = mapped_column(String(8), default="fa")
    status: Mapped[str] = mapped_column(String(16), default="planning")  # planning|done|failed
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_nights: Mapped[int] = mapped_column(Integer, default=1)
    travelers: Mapped[int] = mapped_column(Integer, default=1)
    budget_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class TripMessage(IdMixin, Base):
    __tablename__ = "trip_messages"
    __table_args__ = (Index("ix_trip_messages_trip", "trip_id", "created_at"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16), default="text")


class TripPreferences(IdMixin, Base):
    __tablename__ = "trip_preferences"
    __table_args__ = (UniqueConstraint("trip_id", "key", name="uq_trip_pref"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ------------------------------------------------------------------ results
class Place(IdMixin, Base):
    __tablename__ = "places"

    name: Mapped[str] = mapped_column(String(240), index=True)
    place_type: Mapped[str] = mapped_column(String(32), default="")
    city: Mapped[str] = mapped_column(String(120), default="", index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="confirmed")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SourceRecord(IdMixin, Base):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(240))
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Itinerary(IdMixin, Base):
    __tablename__ = "itineraries"
    __table_args__ = (Index("ix_itineraries_trip_created", "trip_id", "created_at"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ItineraryDay(IdMixin, Base):
    __tablename__ = "itinerary_days"
    __table_args__ = (
        Index("ix_itinerary_days_itinerary_day", "itinerary_id", "day_number"),
    )

    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE")
    )
    day_number: Mapped[int] = mapped_column(Integer)
    day_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    city: Mapped[str] = mapped_column(String(120), default="")
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ------------------------------------------------------------------- agents
class AgentRun(IdMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_trip", "trip_id", "created_at"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    node: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="ok")
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ToolRun(IdMixin, Base):
    __tablename__ = "tool_runs"

    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=True
    )
    tool: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="ok")
    duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)


# ------------------------------------------------------------------- share
class ShareLink(IdMixin, Base):
    __tablename__ = "share_links"
    __table_args__ = (UniqueConstraint("trip_id", "token", name="uq_share_trip_token"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), index=True, default=lambda: uuid.uuid4().hex)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AffiliateClick(IdMixin, Base):
    __tablename__ = "affiliate_clicks"

    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(32))
    target_url: Mapped[str] = mapped_column(Text)
    affiliate_id: Mapped[str] = mapped_column(String(64), default="")


class WebhookEvent(IdMixin, Base):
    """A processed payment webhook, kept for idempotency.

    A duplicate delivery of the same provider event id must be a no-op - the
    unique constraint below makes the second insert fail loudly instead of
    double-crediting a subscription.
    """

    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_event"),)

    provider: Mapped[str] = mapped_column(String(16))  # mock|stripe|zarinpal
    event_id: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ----------------------------------------------------------------- expenses
class Expense(IdMixin, Base):
    """One recorded expense during a trip (Live Mode burn-down)."""

    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expenses_trip_created", "trip_id", "created_at"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(32))  # food|transport|hotel|ticket|other
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="TOMAN")
    #: Amount normalised to the trip currency at recording time (documented rate).
    amount_in_trip_currency: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text, default="")
