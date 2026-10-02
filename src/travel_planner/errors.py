"""Shared exception hierarchy.

These live in their own module so that both ``config`` and ``llm`` can raise and catch the
same classes without importing each other. ``config`` must stay importable with no
dependencies beyond pydantic (audit bug B3).
"""

from __future__ import annotations


class TravelPlannerError(RuntimeError):
    """Base class for every error raised by this package."""


class ConfigurationError(TravelPlannerError):
    """A required credential or endpoint is missing or invalid."""


class LLMError(TravelPlannerError):
    """Base class for model-layer failures."""


class LLMConfigurationError(ConfigurationError):
    """The model provider cannot be constructed (missing key, missing base URL)."""


class LLMResponseError(LLMError):
    """The model returned something unusable (bad JSON, refusal, empty content)."""


class ProviderError(TravelPlannerError):
    """Base class for data-provider failures."""


class ProviderUnavailableError(ProviderError):
    """A provider could not answer. The caller should fall back down the chain.

    This is **not** a fatal error: the registry catches it and tries the next provider.
    """


class CircuitOpenError(ProviderUnavailableError):
    """A provider's circuit breaker is open after repeated failures."""


class ScrapingNotPermittedError(ProviderError):
    """robots.txt or the site's terms forbid automated access. Never bypassed."""


class ValidationOutcomeError(TravelPlannerError):
    """Structured validation failed in a way the caller must handle explicitly."""
