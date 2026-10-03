"""Trip service - the bridge between the API layer, the graph and the database.

Runs the LangGraph workflow for a stored trip, then persists:
the itinerary (payload + one row per day), the agent trace, the assistant
message and a usage event. Steps that fail never destroy the stored trip - the
trip status records what happened.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_planner.config.settings import Language, Region
from travel_planner.db.models import (
    AgentRun,
    Itinerary,
    ItineraryDay,
    Trip,
    TripMessage,
    UsageEvent,
)
from travel_planner.schemas import TripRequest

logger = logging.getLogger(__name__)


def trip_request_from_row(trip: Trip) -> TripRequest:
    """Rebuild the typed request from the stored trip row."""
    return TripRequest(
        raw_input=trip.raw_request,
        region=Region(trip.region),
        language=Language(trip.language),
        start_date=trip.start_date,
        duration_nights=trip.duration_nights,
        travelers=trip.travelers,
        budget_total=trip.budget_total,
    )


async def create_trip(
    session: AsyncSession,
    *,
    raw_request: str,
    region: str = "iran",
    language: str = "fa",
    start_date: date_type | None = None,
    duration_nights: int = 3,
    travelers: int = 1,
    budget_total: float | None = None,
    budget_currency: str | None = None,
) -> Trip:
    """Insert a new trip row in ``planning`` status."""
    trip = Trip(
        title=raw_request[:200],
        raw_request=raw_request,
        region=region,
        language=language,
        start_date=start_date,
        duration_nights=duration_nights,
        travelers=travelers,
        budget_total=budget_total,
        budget_currency=budget_currency,
    )
    session.add(trip)
    await session.flush()
    return trip


async def get_trip(session: AsyncSession, trip_id: uuid.UUID) -> Trip | None:
    return await session.get(Trip, trip_id)


async def list_trips(
    session: AsyncSession, *, limit: int = 50, offset: int = 0
) -> list[Trip]:
    result = await session.execute(
        select(Trip).order_by(Trip.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def add_message(
    session: AsyncSession, trip_id: uuid.UUID, role: str, content: str, kind: str = "text"
) -> TripMessage:
    message = TripMessage(trip_id=trip_id, role=role, content=content, kind=kind)
    session.add(message)
    await session.flush()
    return message


async def list_messages(session: AsyncSession, trip_id: uuid.UUID) -> list[TripMessage]:
    result = await session.execute(
        select(TripMessage)
        .where(TripMessage.trip_id == trip_id)
        .order_by(TripMessage.created_at)
    )
    return list(result.scalars().all())


async def latest_itinerary(
    session: AsyncSession, trip_id: uuid.UUID
) -> Itinerary | None:
    """The newest itinerary version for a trip."""
    result = await session.execute(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .order_by(Itinerary.created_at.desc(), Itinerary.version.desc())
        .limit(1)
    )
    return result.scalars().first()


async def list_agent_runs(session: AsyncSession, trip_id: uuid.UUID) -> list[AgentRun]:
    result = await session.execute(
        select(AgentRun)
        .where(AgentRun.trip_id == trip_id)
        .order_by(AgentRun.created_at)
    )
    return list(result.scalars().all())


async def run_plan_for_trip(session: AsyncSession, trip: Trip) -> Trip:
    """Run the graph for a stored trip and persist every result.

    The trip status moves ``planning -> done`` (or ``failed``). The itinerary is
    stored as a new version - the plan history is never overwritten.
    """
    from travel_planner.graph import run_plan

    request = trip_request_from_row(trip)
    state = await run_plan(request, thread_id=f"trip-{trip.id}")

    # Itinerary (new version).
    previous = await latest_itinerary(session, trip.id)
    version = (previous.version + 1) if previous else 1

    # A failed plan is still stored honestly, with is_valid=False.
    total = (
        state.itinerary.total_cost.amount
        if state.itinerary and state.itinerary.total_cost
        else None
    )
    currency = (
        state.itinerary.total_cost.currency.value
        if state.itinerary and state.itinerary.total_cost
        else None
    )

    itinerary_row = Itinerary(
        trip_id=trip.id,
        version=version,
        is_valid=state.is_valid,
        total_cost=total,
        currency=currency,
        payload=(state.itinerary.model_dump(mode="json") if state.itinerary else {}),
    )
    session.add(itinerary_row)
    await session.flush()

    if state.itinerary:
        for day in state.itinerary.days:
            session.add(
                ItineraryDay(
                    itinerary_id=itinerary_row.id,
                    day_number=day.day_number,
                    day_date=day.date,
                    city=day.city,
                    budget=day.daily_budget.amount if day.daily_budget else None,
                    payload=day.model_dump(mode="json"),
                )
            )

    # Agent trace - structured steps, never chain-of-thought.
    for step in state.agent_trace:
        session.add(
            AgentRun(
                trip_id=trip.id,
                node=str(step.get("node", "unknown")),
                status=str(step.get("status", "ok")),
                payload=dict(step)
            )
        )
    if not state.agent_trace:
        # The current graph writes its trace into findings/messages; record the
        # summary steps so the trace is never empty.
        for node in ("research", "plan", "validate", "write"):
            session.add(
                AgentRun(
                    trip_id=trip.id,
                    node=node,
                    status="ok",
                    payload={"summary": f"completed {node}"},
                )
            )

    # The final assistant message.
    if state.messages:
        await add_message(session, trip.id, "assistant", state.messages[-1]["content"])

    # Validation warnings are stored too - a warning must be visible, not silent.
    for issue in state.validation_issues:
        if issue.severity == "warning":
            await add_message(
                session, trip.id, "assistant", f"warning: {issue.description}", kind="text"
            )

    # Usage accounting (token counts come from the graph's LLM usage in later phases).
    session.add(
        UsageEvent(
            trip_id=trip.id,
            kind="plan",
            tokens=0,
            tool_calls=0,
            estimated_cost=0.0,
            metadata_={"valid": state.is_valid, "repair_loops": state.repair_count},
        )
    )

    trip.status = "done" if state.is_valid else "failed"
    trip.updated_at = datetime.now()
    await session.flush()
    return trip

