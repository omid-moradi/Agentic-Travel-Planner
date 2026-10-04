"""MCP server tests - the protocol layer, offline."""

from __future__ import annotations

import json

import pytest

from travel_planner.mcp.server import handle_message


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the mock LLM so the tests never touch the network."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from travel_planner.config.settings import reload_settings
    from travel_planner.llm import reset_llm_cache

    reload_settings()
    reset_llm_cache()
    yield
    reload_settings()
    reset_llm_cache()


class TestProtocol:
    async def test_initialize(self) -> None:
        response = await handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert response["id"] == 1
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "agentic-travel-planner"

    async def test_tools_list(self) -> None:
        response = await handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in response["result"]["tools"]}
        assert {"plan_trip", "get_health"} <= names
        # Every tool carries a description and a JSON schema.
        for tool in response["result"]["tools"]:
            assert tool["description"]
            assert tool["inputSchema"]["type"] == "object"

    async def test_unknown_method_gets_error(self) -> None:
        response = await handle_message({"jsonrpc": "2.0", "id": 3, "method": "nothing/here", "params": {}})
        assert response["error"]["code"] == -32601

    async def test_unknown_tool_gets_error(self) -> None:
        response = await handle_message(
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}}
        )
        assert response["error"]["code"] == -32602


class TestTools:
    async def test_plan_trip_offline(self) -> None:
        response = await handle_message(
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "plan_trip",
                    "arguments": {"request": "Tehran for 1 night", "duration_nights": 1},
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["valid"] is True
        assert payload["days"] == 1
        assert payload["total_cost"] > 0
        assert payload["currency"] == "TOMAN"

    async def test_get_health(self) -> None:
        response = await handle_message(
            {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "get_health", "arguments": {}}}
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["server"]["name"] == "agentic-travel-planner"
        assert payload["llm"]["provider"] == "mock"

    async def test_tool_exception_is_an_rpc_error_not_a_crash(self) -> None:
        """A crashing handler must return a JSON-RPC error, not kill the server."""
        from travel_planner.mcp import server as mcp_server

        async def _boom(_arguments: dict[str, object]) -> dict[str, object]:
            msg = "injected failure"
            raise RuntimeError(msg)

        original = mcp_server.TOOLS["get_health"]["handler"]
        mcp_server.TOOLS["get_health"]["handler"] = _boom
        try:
            response = await handle_message(
                {"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "get_health", "arguments": {}}}
            )
        finally:
            mcp_server.TOOLS["get_health"]["handler"] = original
        assert response["error"]["code"] == -32000
        assert "injected failure" in response["error"]["message"]


class TestCoreIndependence:
    def test_core_never_imports_the_mcp_module(self) -> None:
        """The master prompt: the core app must work without the MCP server."""
        import pathlib

        src_root = pathlib.Path("src/travel_planner")
        offenders = [
            str(path)
            for path in src_root.rglob("*.py")
            if "mcp" not in str(path) and "travel_planner.mcp" in path.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"core modules importing MCP: {offenders}"
