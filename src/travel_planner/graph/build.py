"""Build the LangGraph workflow.

Shape (phase 2, demo mode):

    START -> research fan-out (9 nodes, parallel) -> plan -> validate
          -> valid ? write -> END
          -> invalid & repair_count < max ? replan -> validate
          -> otherwise -> write -> END  (best effort, with warnings)

The critic/replanner loop is bounded by ``max_repair_loops`` on the state; when the
budget is exhausted the best-effort plan is written out with its warnings attached.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from travel_planner.graph.nodes import (
    plan_itinerary,
    research_accommodation,
    research_culture,
    research_events,
    research_places,
    research_requirements,
    research_restaurants,
    research_safety,
    research_transport,
    research_weather,
    validate_itinerary,
    write_output,
)
from travel_planner.schemas import TravelState

#: A node reads the whole state and returns a partial update.
NodeFn = Callable[[TravelState], dict[str, Any]]

_RESEARCH_NODES: dict[str, NodeFn] = {
    "research_places": research_places,
    "research_accommodation": research_accommodation,
    "research_restaurants": research_restaurants,
    "research_transport": research_transport,
    "research_weather": research_weather,
    "research_events": research_events,
    "research_culture": research_culture,
    "research_safety": research_safety,
    "research_requirements": research_requirements,
}


def _after_validate(state: TravelState) -> str:
    """Conditional edge: repair once, then give up and write best-effort."""
    if state.is_valid:
        return "write"
    if state.repair_count < state.max_repair_loops:
        return "replan"
    return "write"


def _replan(state: TravelState) -> dict[str, object]:
    """Bounded repair: re-run the planner and increment the repair counter.

    The planner is deterministic, so a re-run only helps if the request changed;
    its real purpose in this phase is to keep the loop bounded and observable.
    """
    from travel_planner.graph.nodes.planner import plan_itinerary as plan

    update = plan(state)
    return {**update, "repair_count": state.repair_count + 1, "current_step": "replan"}


def build_graph(checkpointer: Any | None = None) -> CompiledStateGraph[TravelState, Any, Any, Any]:
    """Assemble the workflow. ``checkpointer`` defaults to an in-memory saver."""
    builder = StateGraph(TravelState)

    # Fan-out: every research node runs in parallel from START.
    for name, fn in _RESEARCH_NODES.items():
        builder.add_node(name, fn)  # type: ignore[call-overload]
        builder.add_edge(START, name)

    # Fan-in: all research nodes converge on the planner.
    for name in _RESEARCH_NODES:
        builder.add_edge(name, "plan")

    builder.add_node("plan", plan_itinerary)
    builder.add_node("validate", validate_itinerary)
    builder.add_node("replan", _replan)
    builder.add_node("write", write_output)

    builder.add_edge("plan", "validate")
    builder.add_conditional_edges("validate", _after_validate, {"write": "write", "replan": "replan"})
    builder.add_edge("replan", "validate")
    builder.add_edge("write", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())


def initial_state(request: Any) -> TravelState:
    """Build the entry state for a trip request."""
    return TravelState(request=request)


async def run_plan(request: Any, *, thread_id: str = "trip-1") -> TravelState:
    """Convenience wrapper: run the whole graph and return the final state."""
    from uuid import uuid4

    graph = build_graph()
    final = await graph.ainvoke(
        initial_state(request),
        config={
            "recursion_limit": 30,
            "configurable": {"thread_id": thread_id or uuid4().hex},
        },
    )
    return TravelState.model_validate(final)
