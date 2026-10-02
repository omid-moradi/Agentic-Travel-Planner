"""Provider-agnostic model layer.

The rest of the codebase never imports an OpenAI client directly; it asks
:func:`get_llm` for a :class:`TravelPlannerLLM` and calls high-level methods.

Supported providers (``LLM_PROVIDER``):

===============  ==========================================================
``apmix``        OpenAI-compatible gateway (``https://api.apmix.ai/v1``)
``openai``       the official OpenAI API
``openai_compatible``  any other OpenAI-compatible base URL
``ollama``       a local Ollama server through its OpenAI-compatible endpoint
``mock``         offline, deterministic, zero network - used by demo mode
===============  ==========================================================

Two behaviours matter for this product and are enforced here rather than in each agent:

1. **No chain-of-thought.** Some gateways return a ``reasoning_content`` field. It is
   stripped by :func:`_strip_reasoning` and never returned to callers, persisted or
   shown in the UI.
2. **Bounded tool calls.** The development gateway emits parallel tool calls. The number
   of tool calls per turn is capped by ``LLM_MAX_PARALLEL_TOOL_CALLS`` and every tool
   invocation is expected to be idempotent.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from travel_planner.config.settings import LLMProvider, Settings, get_settings
from travel_planner.errors import LLMConfigurationError, LLMError, LLMResponseError

logger = logging.getLogger(__name__)

Role = Literal["system", "user", "assistant", "tool"]

#: Field name used by OpenAI-compatible gateways to carry hidden reasoning.
REASONING_FIELD = "reasoning_content"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Usage:
    """Token accounting for one or more model calls."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass(frozen=True, slots=True)
class LLMResult:
    """The outcome of a single model call, with reasoning already removed."""

    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    """A provider-neutral chat message."""

    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None


def system(content: str) -> Message:
    return Message(role="system", content=content)


def user(content: str) -> Message:
    return Message(role="user", content=content)


def assistant(content: str) -> Message:
    return Message(role="assistant", content=content)


def tool_result(name: str, tool_call_id: str, content: str) -> Message:
    return Message(role="tool", content=content, name=name, tool_call_id=tool_call_id)


class TravelPlannerLLM(ABC):
    """Interface every provider implements."""

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> LLMResult:
        """Run one completion."""

    @abstractmethod
    async def complete_json(
        self,
        messages: Sequence[Message],
        schema: type[Any],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[Any, Usage]:
        """Run one completion that must parse into ``schema``.

        Implementations retry with a repair prompt when the model returns invalid JSON.
        """

    async def aclose(self) -> None:
        """Release provider resources. Safe to call more than once."""
        return None


class MockLLM(TravelPlannerLLM):
    """Deterministic offline provider for demo mode and tests.

    It never touches the network and always produces something schema-shaped so that the
    whole pipeline can be exercised with zero API keys.
    """

    def __init__(self, model: str = "mock") -> None:
        super().__init__(model)
        self._calls = 0

    @staticmethod
    def _shape_for(schema: type[Any], prompt: str) -> dict[str, Any]:
        """Build a minimal object satisfying ``schema`` so demo mode stays schema-valid."""
        json_schema = getattr(schema, "model_json_schema", None)
        properties: dict[str, Any] = {}
        if callable(json_schema):
            properties = json_schema().get("properties", {})
        payload: dict[str, Any] = {}
        for name, spec in properties.items():
            kind = spec.get("type")
            default = spec.get("default")
            if default is not None:
                payload[name] = default
            elif kind == "string":
                payload[name] = f"mock {name}"
            elif kind == "integer":
                payload[name] = 0
            elif kind == "number":
                payload[name] = 0.0
            elif kind == "boolean":
                payload[name] = False
            elif kind == "array":
                payload[name] = []
            elif kind == "object":
                payload[name] = {}
            else:
                payload[name] = f"mock {name} ({prompt[:40]})"
        return payload

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> LLMResult:
        self._calls += 1
        last = messages[-1].content if messages else ""
        if json_mode:
            payload: dict[str, Any] = {"summary": f"mock summary for: {last[:80]}"}
            content = json.dumps(payload, ensure_ascii=False)
        else:
            content = f"[mock:{self.model}] {last[:200]}"
        return LLMResult(
            content=content,
            usage=Usage(
                prompt_tokens=sum(len(m.content) for m in messages) // 4,
                completion_tokens=len(content) // 4,
                total_tokens=(sum(len(m.content) for m in messages) + len(content)) // 4,
            ),
            model=self.model,
            finish_reason="stop",
        )

    async def complete_json(
        self,
        messages: Sequence[Message],
        schema: type[Any],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[Any, Usage]:
        result = await self.complete(messages, temperature=temperature, json_mode=True)
        last = messages[-1].content if messages else ""
        shaped = self._shape_for(schema, last)
        try:
            parsed = json.loads(result.content)
        except json.JSONDecodeError:  # pragma: no cover - mock always emits JSON
            parsed = shaped
        if not isinstance(parsed, dict) or not _satisfies(parsed, schema):
            # The generic mock payload is not schema-shaped; use the shaped one instead.
            parsed = shaped
        if hasattr(schema, "model_validate"):
            instance = schema.model_validate(parsed)
        else:  # pragma: no cover - defensive
            instance = schema(**parsed)
        return instance, result.usage


class OpenAICompatibleLLM(TravelPlannerLLM):
    """Any provider speaking the OpenAI chat-completions protocol."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float,
        timeout: float,
        max_tokens: int,
        max_retries: int,
        max_parallel_tool_calls: int,
    ) -> None:
        super().__init__(model)
        from openai import AsyncOpenAI  # imported lazily so mock mode needs no SDK

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_parallel_tool_calls = max_parallel_tool_calls
        #: Endpoint actually in use, kept for diagnostics and tests.
        self.base_url = base_url
        self.max_parallel_tool_calls = max_parallel_tool_calls

    def _to_payload(self, messages: Sequence[Message]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for message in messages:
            item: dict[str, Any] = {"role": message.role, "content": message.content}
            if message.name is not None:
                item["name"] = message.name
            if message.tool_call_id is not None:
                item["tool_call_id"] = message.tool_call_id
            payload.append(item)
        return payload

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_payload(messages),
            "temperature": self._temperature if temperature is None else temperature,
            "max_tokens": self._max_tokens if max_tokens is None else max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if tools:
            kwargs["tools"] = list(tools)
            kwargs["tool_choice"] = "auto"
            # Ask the gateway not to fan out more calls than we are willing to execute.
            kwargs["parallel_tool_calls"] = False

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # openai raises a large exception hierarchy
            msg = f"LLM call failed ({self.model}): {exc}"
            raise LLMError(msg) from exc

        choice = response.choices[0] if response.choices else None
        if choice is None:
            msg = f"LLM returned no choices ({self.model})"
            raise LLMResponseError(msg)

        message = choice.message
        # reasoning_content is dropped here and never leaves this class.
        content = _strip_reasoning(getattr(message, "content", None))
        calls = _parse_tool_calls(getattr(message, "tool_calls", None))
        if len(calls) > self._max_parallel_tool_calls:
            logger.warning(
                "Capping %d tool calls to %d for this turn", len(calls), self._max_parallel_tool_calls
            )
            calls = calls[: self._max_parallel_tool_calls]

        usage = Usage(
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
        )
        return LLMResult(
            content=content,
            tool_calls=calls,
            usage=usage,
            model=getattr(response, "model", self.model) or self.model,
            finish_reason=getattr(choice, "finish_reason", None),
        )

    async def complete_json(
        self,
        messages: Sequence[Message],
        schema: type[Any],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[Any, Usage]:
        """Complete, parse, and repair once if the model returned invalid JSON.

        Models wrap JSON in markdown fences even with ``json_object`` mode, so extraction
        is attempted before parsing.
        """
        result = await self.complete(
            messages, temperature=temperature, max_tokens=max_tokens, json_mode=True
        )
        payload = extract_json(result.content)
        if payload is not None:
            return _validate(payload, schema), result.usage

        logger.warning("Model returned unparsable JSON; retrying with a repair prompt")
        repair_messages = [
            *messages,
            Message(
                role="user",
                content=(
                    "Your previous reply was not valid JSON. Reply with ONLY a single JSON "
                    f"object matching this schema, no markdown fences:\n{_schema_hint(schema)}"
                ),
            ),
        ]
        retry = await self.complete(
            repair_messages, temperature=0.0, max_tokens=max_tokens, json_mode=True
        )
        payload = extract_json(retry.content)
        if payload is None:
            msg = f"Model did not return valid JSON after a repair attempt: {retry.content[:300]}"
            raise LLMResponseError(msg)
        return _validate(payload, schema), result.usage + retry.usage

    async def aclose(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            await close()


def _satisfies(payload: Mapping[str, Any], schema: type[Any]) -> bool:
    """True when ``payload`` validates against ``schema`` without raising."""
    try:
        _validate(payload, schema)
    except Exception:
        return False
    return True


def _validate(payload: Mapping[str, Any], schema: type[Any]) -> Any:
    if hasattr(schema, "model_validate"):
        return schema.model_validate(dict(payload))
    return schema(**dict(payload))  # pragma: no cover - defensive


def _strip_reasoning(content: Any) -> str:
    """Return the user-visible content only.

    Some gateways (including the development gateway) return a ``reasoning_content``
    field separately from ``content``. If a provider inlines reasoning into ``content``,
    any ``<think>`` block is removed as well.
    """
    if content is None:
        return ""
    text = content if isinstance(content, str) else str(content)
    lowered = text.lower()
    if "<think>" in lowered and "</think>" in lowered:
        head, _, rest = text.partition("<think>")
        _, _, tail = rest.partition("</think>")
        text = head + tail
    return text.strip()


def _parse_tool_calls(raw: Any) -> tuple[ToolCall, ...]:
    if not raw:
        return ()
    calls: list[ToolCall] = []
    for item in raw:
        function = getattr(item, "function", None)
        if function is None:
            continue
        name = getattr(function, "name", "") or ""
        raw_args = getattr(function, "arguments", "") or "{}"
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            logger.warning("Tool call %s had unparsable arguments; treating as empty", name)
            arguments = {}
        calls.append(ToolCall(id=getattr(item, "id", "") or name, name=name, arguments=arguments))
    return tuple(calls)


def extract_json(text: str) -> dict[str, Any] | None:
    """Pull a JSON object out of a model reply, tolerating markdown fences."""
    candidate = text.strip()
    if not candidate:
        return None
    if candidate.startswith("```"):
        _, _, rest = candidate.partition("```")
        rest = rest.partition("\n")[2] if rest.startswith("json") else rest
        candidate = rest.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _schema_hint(schema: type[Any]) -> str:
    json_schema = getattr(schema, "model_json_schema", None)
    if callable(json_schema):
        return json.dumps(json_schema(), ensure_ascii=False)[:2000]
    return getattr(schema, "__name__", str(schema))


def build_llm(settings: Settings | None = None, *, model: str | None = None) -> TravelPlannerLLM:
    """Instantiate the configured provider. Raises only when credentials are required."""
    cfg = settings or get_settings()
    resolved_model = model or cfg.llm_model

    if cfg.llm_provider is LLMProvider.MOCK:
        return MockLLM(resolved_model)

    if cfg.llm_provider is LLMProvider.OPENAI:
        base_url = cfg.llm_base_url or "https://api.openai.com/v1"
    elif cfg.llm_provider is LLMProvider.OLLAMA:
        base_url = cfg.ollama_base_url.rstrip("/") + "/v1"
    else:
        base_url = cfg.llm_base_url.rstrip("/")

    if not base_url:
        msg = f"LLM_BASE_URL is required for provider {cfg.llm_provider.value}"
        raise LLMConfigurationError(msg)

    if cfg.llm_provider is LLMProvider.OLLAMA:
        # A local Ollama server does not authenticate.
        api_key = "ollama"
    else:
        # Raises a clear, actionable message instead of failing at import time.
        api_key = cfg.require_llm_credentials()

    logger.info(
        "LLM provider=%s model=%s base_url=%s", cfg.llm_provider.value, resolved_model, base_url
    )
    return OpenAICompatibleLLM(
        model=resolved_model,
        api_key=api_key,
        base_url=base_url,
        temperature=cfg.llm_temperature,
        timeout=cfg.llm_timeout,
        max_tokens=cfg.llm_max_tokens,
        max_retries=cfg.llm_max_retries,
        max_parallel_tool_calls=cfg.llm_max_parallel_tool_calls,
    )


def build_extraction_llm(settings: Settings | None = None) -> TravelPlannerLLM:
    """Cheaper model used for extraction tasks (model routing, phase 6)."""
    cfg = settings or get_settings()
    if cfg.is_offline or cfg.effective_extraction_model == cfg.llm_model:
        return build_llm(cfg)
    return build_llm(cfg, model=cfg.effective_extraction_model)


_CACHE: dict[str, TravelPlannerLLM] = {}


def get_llm(settings: Settings | None = None, *, model: str | None = None) -> TravelPlannerLLM:
    """Return a cached LLM instance for the given provider/model pair."""
    cfg = settings or get_settings()
    key = f"{cfg.llm_provider.value}:{model or cfg.llm_model}"
    if key not in _CACHE:
        _CACHE[key] = build_llm(cfg, model=model)
    return _CACHE[key]


def reset_llm_cache() -> None:
    """Drop cached clients (used by tests)."""
    _CACHE.clear()


def describe_provider(settings: Settings | None = None) -> dict[str, Any]:
    """Non-secret description of the active model configuration, safe to log or return."""
    cfg = settings or get_settings()
    return {
        "provider": cfg.llm_provider.value,
        "model": cfg.llm_model,
        "base_url": cfg.llm_base_url,
        "offline": cfg.is_offline,
        "has_api_key": cfg.has_llm_credentials,
    }
