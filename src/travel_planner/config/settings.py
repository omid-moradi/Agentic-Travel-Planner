"""Typed, environment-driven application settings.

Design rules (see ``docs/decisions.md`` ADR-003 and audit item B3):

* Settings are **never** validated at import time. A missing API key must not break
  importing a module that does not need a model (tests, CLI ``--help``, provider code).
* Secrets come from the environment only and are never logged or serialised.
* ``get_settings()`` is cached, but ``reload_settings()`` exists for tests.
"""

from __future__ import annotations

import functools
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from travel_planner.errors import LLMConfigurationError

#: A comma-separated provider chain, e.g. ``curated,estimator``.
ProviderChain = Annotated[list[str], NoDecode]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class LLMProvider(StrEnum):
    """Supported model providers.

    ``apmix`` and ``openai_compatible`` speak the OpenAI chat-completions protocol;
    ``ollama`` is reached through its OpenAI-compatible endpoint as well.
    """

    APMIX = "apmix"
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"
    MOCK = "mock"


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Language(StrEnum):
    FA = "fa"
    EN = "en"


class Region(StrEnum):
    IRAN = "iran"
    INTERNATIONAL = "international"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


def _split_csv(value: object) -> object:
    """Accept ``a,b,c`` strings as well as real lists for list-valued settings."""
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


class Settings(BaseSettings):
    """Application settings loaded from the environment and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ app
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON
    default_language: Language = Language.FA
    default_region: Region = Region.IRAN
    max_repair_loops: Annotated[int, Field(ge=0, le=10)] = 2
    max_tool_calls_per_run: Annotated[int, Field(ge=1)] = 40

    # ------------------------------------------------------------------ llm
    llm_provider: LLMProvider = LLMProvider.APMIX
    llm_base_url: str = "https://api.apmix.ai/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "deepseek/deepseek-v4-flash-free"
    llm_extraction_model: str = ""
    llm_temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.4
    llm_timeout: Annotated[float, Field(gt=0)] = 60.0
    llm_max_tokens: Annotated[int, Field(ge=1)] = 4096
    llm_max_retries: Annotated[int, Field(ge=0, le=10)] = 3
    llm_max_parallel_tool_calls: Annotated[int, Field(ge=1, le=16)] = 4
    ollama_base_url: str = "http://localhost:11434"

    # -------------------------------------------------------------- scraping
    scraper_user_agent: str = (
        "AgenticTravelPlannerBot/0.1 "
        "(+https://github.com/omid-moradi/Agentic-Travel-Planner)"
    )
    scraper_rate_limit_per_second: Annotated[float, Field(gt=0)] = 0.5
    scraper_respect_robots: bool = True
    scraper_timeout: Annotated[float, Field(gt=0)] = 20.0
    scraper_max_concurrency: Annotated[int, Field(ge=1)] = 2

    # ----------------------------------------------------------- persistence
    database_url: str = "sqlite+aiosqlite:///./travel_planner.db"
    redis_url: str = ""
    cache_ttl_prices_seconds: Annotated[int, Field(ge=1)] = 10_800
    cache_ttl_place_info_seconds: Annotated[int, Field(ge=1)] = 259_200

    # --------------------------------------------------------------- search
    tavily_api_key: SecretStr = SecretStr("")

    # ------------------------------------------------------------- providers
    hotels_providers: ProviderChain = ["curated", "estimator"]
    transport_providers: ProviderChain = ["curated", "estimator"]
    restaurants_providers: ProviderChain = ["curated", "estimator"]
    ride_fare_providers: ProviderChain = ["estimator"]
    places_providers: ProviderChain = ["fixture", "curated"]
    weather_providers: ProviderChain = ["open_meteo"]
    currency_providers: ProviderChain = ["exchangerate_host"]
    routes_providers: ProviderChain = ["osrm"]
    geocode_providers: ProviderChain = ["nominatim"]
    events_providers: ProviderChain = ["fixture", "curated"]

    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    osrm_base_url: str = "https://router.project-osrm.org"
    valhalla_base_url: str = ""
    neshan_api_key: SecretStr = SecretStr("")
    balad_api_key: SecretStr = SecretStr("")

    # ---------------------------------------------------------- monetization
    billing_enabled: bool = False
    payment_provider: str = "mock"
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    zarinpal_merchant_id: str = ""
    zarinpal_sandbox: bool = True
    enable_iran_gateway: bool = False
    affiliate_hotels_id: str = ""
    affiliate_flights_id: str = ""
    affiliate_activities_id: str = ""
    free_tier_plans_per_month: Annotated[int, Field(ge=0)] = 3
    pro_tier_plans_per_month: Annotated[int, Field(ge=0)] = 50
    guest_trial_enabled: bool = True

    # --------------------------------------------------------------- auth
    #: HS256 secret for JWTs. MUST be set in production; the default is for
    #: local/demo use only and a warning is logged when it is used.
    jwt_secret: SecretStr = SecretStr("dev-only-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: Annotated[int, Field(gt=0)] = 60 * 24
    #: Bootstrap admin: the first account created with this email becomes admin.
    admin_bootstrap_email: str = ""

    # ---------------------------------------------------------- validators
    _split_lists = field_validator(
        "hotels_providers",
        "transport_providers",
        "restaurants_providers",
        "ride_fare_providers",
        "places_providers",
        "weather_providers",
        "currency_providers",
        "routes_providers",
        "geocode_providers",
        "events_providers",
        mode="before",
    )(classmethod(lambda cls, v: _split_csv(v)))

    # ----------------------------------------------------------- properties
    @property
    def is_offline(self) -> bool:
        """True when no network call should be attempted (mock provider)."""
        return self.llm_provider is LLMProvider.MOCK

    @property
    def has_llm_credentials(self) -> bool:
        """True when an API key is configured. Never raises - see module docstring."""
        return bool(self.llm_api_key.get_secret_value().strip())

    @property
    def has_tavily_credentials(self) -> bool:
        return bool(self.tavily_api_key.get_secret_value().strip())

    @property
    def effective_extraction_model(self) -> str:
        """Model used for cheap extraction tasks; falls back to the main model."""
        return self.llm_extraction_model.strip() or self.llm_model

    def require_llm_credentials(self) -> str:
        """Return the API key or raise a clear, actionable error.

        Called lazily by the model factory so importing this module never fails.
        """
        key = self.llm_api_key.get_secret_value().strip()
        if not key:
            msg = (
                f"No API key configured for LLM_PROVIDER={self.llm_provider.value}. "
                "Set LLM_API_KEY in .env, or use LLM_PROVIDER=mock for offline demo mode."
            )
            raise LLMConfigurationError(msg)
        return key

    def require_tavily_credentials(self) -> str:
        key = self.tavily_api_key.get_secret_value().strip()
        if not key:
            msg = "TAVILY_API_KEY is not set; web search is unavailable."
            raise LLMConfigurationError(msg)
        return key

    def redacted(self) -> dict[str, object]:
        """A dict safe to log: every secret is replaced by a presence marker."""
        out: dict[str, object] = {}
        for name, value in self.model_dump().items():
            out[name] = "***set***" if isinstance(value, str) and _is_secret(name) else value
        return out


_SECRET_NAMES = ("api_key", "secret_key", "webhook_secret", "merchant_id")


def _is_secret(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(marker in lowered for marker in _SECRET_NAMES)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


def reload_settings() -> Settings:
    """Clear the cache and re-read the environment (used by tests)."""
    get_settings.cache_clear()
    return get_settings()
