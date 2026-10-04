"""Expense tracking with currency conversion and budget burn-down.

Conversion uses a documented static rate table (offline, labelled estimated)
behind the same interface a live provider will replace in phase 8. The
burn-down compares recorded spend against the itinerary's estimated total.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.config.regions import Currency
from travel_planner.db.models import Expense
from travel_planner.errors import ProviderUnavailableError
from travel_planner.schemas import DataStatus, PriceEstimate

#: Static conversion rates INTO TOMAN (documented heuristic, 2026-10).
#: A live currency provider replaces this table behind the same function.
_TOMAN_PER_UNIT: dict[str, float] = {
    "TOMAN": 1.0,
    "IRR": 0.1,
    "USD": 100_000.0,
    "EUR": 105_000.0,
    "GBP": 125_000.0,
    "TRY": 2_800.0,
    "AED": 27_000.0,
}


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert between supported currencies via the static table."""
    source = from_currency.upper()
    target = to_currency.upper()
    if source not in _TOMAN_PER_UNIT or target not in _TOMAN_PER_UNIT:
        msg = f"no conversion rate for {from_currency!r} -> {to_currency!r}"
        raise ProviderUnavailableError(msg)
    toman = amount * _TOMAN_PER_UNIT[source]
    return toman / _TOMAN_PER_UNIT[target]


@dataclass(frozen=True, slots=True)
class BurnDown:
    """The trip's spend against its estimated budget."""

    spent: float
    budget: float | None
    remaining: float | None
    currency: str
    by_category: dict[str, float]
    status: str


async def add_expense(
    session: AsyncSession,
    *,
    trip_id: uuid.UUID,
    title: str,
    amount: float,
    currency: str,
    category: str,
    day_number: int | None = None,
    note: str = "",
    trip_currency: str = "TOMAN",
) -> Expense:
    """Record one expense, normalised into the trip currency at insert time."""
    normalised = convert(amount, currency, trip_currency)
    expense = Expense(
        trip_id=trip_id,
        day_number=day_number,
        category=category,
        title=title,
        amount=amount,
        currency=currency.upper(),
        amount_in_trip_currency=normalised,
        note=note,
    )
    session.add(expense)
    await session.flush()
    return expense


async def list_expenses(session: AsyncSession, trip_id: uuid.UUID) -> list[Expense]:
    result = await session.execute(
        select(Expense).where(Expense.trip_id == trip_id).order_by(Expense.created_at)
    )
    return list(result.scalars().all())


async def burn_down(
    session: AsyncSession,
    *,
    trip_id: uuid.UUID,
    estimated_total: float | None,
    trip_currency: str = "TOMAN",
) -> BurnDown:
    """Spend summary against the estimated budget, by category."""
    expenses = await list_expenses(session, trip_id)
    by_category: dict[str, float] = {}
    for expense in expenses:
        by_category[expense.category] = (
            by_category.get(expense.category, 0.0) + expense.amount_in_trip_currency
        )
    spent = sum(by_category.values())
    remaining = (estimated_total - spent) if estimated_total is not None else None
    return BurnDown(
        spent=spent,
        budget=estimated_total,
        remaining=remaining,
        currency=trip_currency,
        by_category=by_category,
        status=DataStatus.ESTIMATED.value,
    )


def burn_down_price(burn: BurnDown) -> PriceEstimate:
    """The spent amount as a labelled price (always estimated)."""
    return PriceEstimate(
        amount=burn.spent,
        currency=Currency.TOMAN,
        status=DataStatus.ESTIMATED,
        note="sum of recorded expenses, converted at the documented static rate",
    )
