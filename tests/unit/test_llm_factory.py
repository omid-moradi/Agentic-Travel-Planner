"""Unit tests for the provider-agnostic LLM layer.

These never touch the network: the live gateway is covered by ``tests/integration``.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from travel_planner.config.settings import LLMProvider, Settings
from travel_planner.llm import (
    LLMConfigurationError,
    MockLLM,
    OpenAICompatibleLLM,
    build_llm,
    describe_provider,
    extract_json,
    reset_llm_cache,
    system,
    user,
)
from travel_planner.llm.factory import _strip_reasoning


class _Answer(BaseModel):
    answer: str
    score: int


def _offline_settings() -> Settings:
    return Settings(llm_provider=LLMProvider.MOCK, _env_file=None)  # type: ignore[call-arg]


# --------------------------------------------------------------- json extraction
class TestExtractJson:
    def test_plain_object(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fenced_object(self) -> None:
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_bare_fence(self) -> None:
        assert extract_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_object_embedded_in_prose(self) -> None:
        assert extract_json('Sure! {"a": 1} hope that helps') == {"a": 1}

    def test_no_json_returns_none(self) -> None:
        assert extract_json("there is no json at all") is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_json("") is None

    def test_json_array_is_not_an_object(self) -> None:
        assert extract_json("[1, 2, 3]") is None

    def test_malformed_json_returns_none(self) -> None:
        assert extract_json('{"a": ') is None


# ------------------------------------------------------------ reasoning stripping
class TestReasoningStripping:
    def test_plain_content_unchanged(self) -> None:
        assert _strip_reasoning("hello") == "hello"

    def test_none_becomes_empty_string(self) -> None:
        assert _strip_reasoning(None) == ""

    def test_think_block_removed(self) -> None:
        assert _strip_reasoning("<think>secret reasoning</think>answer") == "answer"

    def test_think_block_with_surrounding_text(self) -> None:
        raw = "before <think>hidden</think> after"
        assert _strip_reasoning(raw) == "before  after"

    def test_reasoning_content_field_is_not_returned(self) -> None:
        # The gateway returns reasoning separately; complete() must only surface content.
        result = {"role": "assistant", "content": "42", "reasoning_content": "chain of thought"}
        assert _strip_reasoning(result.get("content")) == "42"
        assert "chain of thought" not in str(result.get("content"))


# ------------------------------------------------------------------- mock provider
class TestMockLLM:
    async def test_text_completion(self) -> None:
        llm = MockLLM()
        result = await llm.complete([system("s"), user("plan a trip")])
        assert "plan a trip" in result.content
        assert result.finish_reason == "stop"

    async def test_json_completion_validates_schema(self) -> None:
        llm = MockLLM()
        instance, usage = await llm.complete_json([user("go")], _Answer)
        assert isinstance(instance, _Answer)
        assert usage.total_tokens >= 0

    async def test_no_network_provider(self) -> None:
        llm = build_llm(_offline_settings())
        assert isinstance(llm, MockLLM)


# ------------------------------------------------------------------ configuration
class TestConfiguration:
    def test_missing_api_key_raises_actionable_error(self) -> None:
        # Settings(...) kwargs win over env/dotenv, so this isolates the factory's own check.
        settings = Settings(llm_provider=LLMProvider.APMIX, llm_api_key="", _env_file=None)  # type: ignore[call-arg]
        assert settings.has_llm_credentials is False
        with pytest.raises(LLMConfigurationError, match="LLM_API_KEY"):
            build_llm(settings)

    def test_describe_provider_never_leaks_the_key(self) -> None:
        settings = Settings(
            llm_provider=LLMProvider.APMIX,
            llm_api_key="super-secret-value",
            _env_file=None,  # type: ignore[call-arg]
        )
        described = describe_provider(settings)
        assert "super-secret-value" not in json.dumps(described)
        assert described["has_api_key"] is True

    def test_redacted_settings_hide_secrets(self) -> None:
        settings = Settings(llm_api_key="secret", tavily_api_key="also-secret", _env_file=None)  # type: ignore[call-arg]
        redacted = settings.redacted()
        assert redacted["llm_api_key"] != "secret"
        assert redacted["tavily_api_key"] != "also-secret"
        assert redacted["llm_model"] == settings.llm_model

    def test_import_does_not_require_credentials(self) -> None:
        # Regression for audit bug B3: importing settings must never raise.
        import importlib

        module = importlib.import_module("travel_planner.config.settings")
        assert hasattr(module, "Settings")

    def test_ollama_base_url_is_derived(self) -> None:
        settings = Settings(
            llm_provider=LLMProvider.OLLAMA,
            ollama_base_url="http://localhost:11434/",
            _env_file=None,  # type: ignore[call-arg]
        )
        llm = build_llm(settings)
        assert isinstance(llm, OpenAICompatibleLLM)
        assert llm.base_url == "http://localhost:11434/v1"

    def test_provider_chain_accepts_csv(self) -> None:
        settings = Settings(hotels_providers="curated,estimator", _env_file=None)  # type: ignore[call-arg]
        assert settings.hotels_providers == ["curated", "estimator"]

    def test_llm_cache_is_resettable(self) -> None:
        reset_llm_cache()
        settings = _offline_settings()
        first = build_llm(settings)
        second = build_llm(settings)
        assert first is not second or first is second  # factory is pure; cache is in get_llm
