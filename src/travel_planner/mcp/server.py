"""A minimal MCP server exposing the core planning tools over stdio.

Protocol: JSON-RPC 2.0 with the Model Context Protocol's basic methods
(initialize, tools/list, tools/call), one JSON object per line.

Design decisions (recorded in STATUS-P8.md):

* **Dependency-free**: the MCP Python SDK is heavy and fast-moving; the wire
  format is simple and this implementation is ~100 auditable lines speaking
  the same protocol, so a standard MCP client can talk to it.
* **The core app never imports this module** - the master prompt requires the
  core to work without the MCP server. Run it explicitly:

      python -m travel_planner.mcp.server
"""

from __future__ import annotations

import json
import sys
from typing import Any

from travel_planner.config.settings import Language, Region
from travel_planner.schemas import TripRequest

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "agentic-travel-planner", "version": "0.1.0"}


async def _tool_plan_trip(arguments: dict[str, Any]) -> dict[str, Any]:
    """Plan a trip with the agentic workflow (offline demo mode)."""
    from travel_planner.graph import run_plan

    request = TripRequest(
        raw_input=str(arguments.get("request", "")),
        region=Region(str(arguments.get("region", "iran"))),
        language=Language(str(arguments.get("language", "fa"))),
        destinations=list(arguments.get("destinations", []) or []),
        duration_nights=arguments.get("duration_nights"),
        travelers=arguments.get("travelers", 1),
        budget_total=arguments.get("budget_total"),
    )
    state = await run_plan(request, thread_id="mcp-1")
    return {
        "valid": state.is_valid,
        "cities": [day.city for day in state.itinerary.days] if state.itinerary else [],
        "days": len(state.itinerary.days) if state.itinerary else 0,
        "total_cost": (
            state.itinerary.total_cost.amount
            if state.itinerary and state.itinerary.total_cost
            else None
        ),
        "currency": (
            state.itinerary.total_cost.currency.value
            if state.itinerary and state.itinerary.total_cost
            else None
        ),
        "warnings": [i.description for i in state.validation_issues if i.severity == "warning"],
        "message": state.messages[-1]["content"] if state.messages else "",
    }


async def _tool_health(_arguments: dict[str, Any]) -> dict[str, Any]:
    """Server + configuration liveness."""
    from travel_planner import __version__
    from travel_planner.config.settings import get_settings
    from travel_planner.llm import describe_provider

    settings = get_settings()
    return {
        "server": SERVER_INFO,
        "product_version": __version__,
        "llm": describe_provider(settings),
        "region": settings.default_region.value,
    }


#: The tool registry: name -> (description, input schema, handler).
TOOLS: dict[str, dict[str, Any]] = {
    "plan_trip": {
        "description": (
            "Plan a trip with the agentic workflow (offline demo mode). "
            "Returns the itinerary summary, validity and warnings."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Natural-language trip request"},
                "region": {"type": "string", "enum": ["iran", "international"]},
                "language": {"type": "string", "enum": ["fa", "en"]},
                "destinations": {"type": "array", "items": {"type": "string"}},
                "duration_nights": {"type": "integer", "minimum": 1},
                "travelers": {"type": "integer", "minimum": 1, "maximum": 50},
                "budget_total": {"type": "number"},
            },
            "required": ["request"],
        },
        "handler": _tool_plan_trip,
    },
    "get_health": {
        "description": "Liveness and configuration summary of the planner.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_health,
    },
}


def _rpc_result(result: dict[str, Any], request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(code: int, message: str, request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


async def handle_message(message: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one JSON-RPC message; unknown methods get a proper error."""
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return _rpc_result(
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
            request_id,
        )
    if method == "tools/list":
        return _rpc_result(
            {
                "tools": [
                    {
                        "name": name,
                        "description": spec["description"],
                        "inputSchema": spec["inputSchema"],
                    }
                    for name, spec in TOOLS.items()
                ]
            },
            request_id,
        )
    if method == "tools/call":
        name = str(params.get("name"))
        spec = TOOLS.get(name)
        if spec is None:
            return _rpc_error(-32602, f"unknown tool {name!r}", request_id)
        try:
            result = await spec["handler"](dict(params.get("arguments") or {}))
            return _rpc_result(
                {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
                request_id,
            )
        except Exception as exc:  # a tool failure is a result, not a crash
            return _rpc_error(-32000, f"{type(exc).__name__}: {exc}", request_id)
    return _rpc_error(-32601, f"method {method!r} not supported", request_id)


async def serve_stdio() -> None:
    """Read JSON lines from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _rpc_error(-32700, "parse error", None)
        else:
            response = await handle_message(message)
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main() -> None:
    import asyncio

    asyncio.run(serve_stdio())


if __name__ == "__main__":
    main()

