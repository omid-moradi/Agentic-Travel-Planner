"""Opt-in live tests against the configured LLM gateway.

These call a real provider and are therefore marked ``live``. They skip automatically when
no API key is configured, so the default suite stays offline and deterministic.

Run them with::

    pytest -m live

The gateway under test is whatever ``LLM_PROVIDER``/``LLM_BASE_URL``/``LLM_MODEL`` point at
(apmix + deepseek-v4-flash-free by default). Nothing here asserts on model prose, only on
the structural guarantees the product depends on.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from pydantic import BaseModel

from travel_planner.config.settings import LLMProvider, Settings, get_settings
from travel_planner.llm import (
    LLMError,
    Message,
    OpenAICompatibleLLM,
    ToolCall,
    build_llm,
    system,
    user,
)

pytestmark = pytest.mark.live

pytest.importorskip("openai", reason="the openai SDK is required for live provider tests")


class _Echo(BaseModel):
    city: str
    days: int


def _live_settings() -> Settings:
    settings = get_settings()
    if settings.llm_provider is LLMProvider.MOCK or not settings.has_llm_credentials:
        pytest.skip("LLM_PROVIDER=mock or no API key configured; skipping live provider tests")
    return settings


@pytest.fixture
async def llm() -> AsyncIterator[OpenAICompatibleLLM]:
    """Function-scoped so the client is closed inside the running event loop.

    A module-scoped async fixture tears down after the loop is closed on Windows, which
    makes ``httpx`` fail with "Event loop is closed".
    """
    client = build_llm(_live_settings())
    assert isinstance(client, OpenAICompatibleLLM)
    try:
        yield client
    finally:
        await client.aclose()


class TestLiveGateway:
    async def test_plain_completion(self, llm: OpenAICompatibleLLM) -> None:
        result = await llm.complete([user("Reply with exactly the word: ready")], max_tokens=32)
        assert result.content
        assert "ready" in result.content.lower()

    async def test_no_reasoning_content_leaks(self, llm: OpenAICompatibleLLM) -> None:
        # The gateway returns a reasoning_content field; it must never reach the caller.
        result = await llm.complete([user("What is 2+2? Answer with the number only.")])
        assert result.content.strip()
        assert "reasoning_content" not in result.content
        assert "<think>" not in result.content.lower()

    async def test_json_mode_matches_schema(self, llm: OpenAICompatibleLLM) -> None:
        instance, usage = await llm.complete_json(
            [system("Return strict JSON only."), user("A 3 day trip to Tehran.")],
            _Echo,
            max_tokens=256,
        )
        assert isinstance(instance, _Echo)
        assert instance.days >= 1
        assert usage.total_tokens >= 0

    async def test_tool_calling_is_supported(self, llm: OpenAICompatibleLLM) -> None:
        tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather for a city.",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ]
        result = await llm.complete(
            [user("What is the weather in Tehran? Use the tool.")], tools=tools, max_tokens=256
        )
        assert result.tool_calls, f"expected a tool call, got: {result.content[:200]}"
        call: ToolCall = result.tool_calls[0]
        assert call.name == "get_weather"
        assert "city" in call.arguments

    async def test_parallel_tool_calls_are_capped(self, llm: OpenAICompatibleLLM) -> None:
        tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Look something up.",
                    "parameters": {
                        "type": "object",
                        "properties": {"q": {"type": "string"}},
                        "required": ["q"],
                    },
                },
            }
        ]
        settings = _live_settings()
        result = await llm.complete(
            [user("Search for Tehran, Shiraz, Isfahan and Tabriz using the tool four times.")],
            tools=tools,
            max_tokens=512,
        )
        assert len(result.tool_calls) <= settings.llm_max_parallel_tool_calls

    async def test_system_message_is_honoured(self, llm: OpenAICompatibleLLM) -> None:
        result = await llm.complete(
            [system("You only answer in Persian, in one short sentence."), user("What is Tehran?")],
            max_tokens=200,
        )
        assert result.content.strip()
        # Persian contains at least one Arabic-script character.
        assert any("\u0600" <= ch <= "\u06ff" for ch in result.content)

    async def test_unreachable_endpoint_raises_llm_error(self) -> None:
        """Failure injection: a dead endpoint must surface as LLMError, not a raw SDK error."""
        settings = _live_settings().model_copy(
            update={"llm_base_url": "http://127.0.0.1:9/v1", "llm_max_retries": 0, "llm_timeout": 3}
        )
        client = build_llm(settings)
        assert isinstance(client, OpenAICompatibleLLM)
        try:
            with pytest.raises(LLMError):
                await client.complete([Message(role="user", content="ping")])
        finally:
            await client.aclose()
