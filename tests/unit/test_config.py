"""Unit tests for typed settings and region profiles."""

from __future__ import annotations

import pytest

from travel_planner.config.regions import (
    INTERNATIONAL_PROFILE,
    IRAN_PROFILE,
    CalendarSystem,
    Currency,
    TextDirection,
    get_profile,
)
from travel_planner.config.settings import (
    Language,
    LLMProvider,
    Region,
    Settings,
    get_settings,
    reload_settings,
)


def _settings(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


class TestSettingsLoading:
    def test_importing_never_raises(self) -> None:
        # Regression for audit bug B3: no import-time validation, ever.
        import importlib

        module = importlib.import_module("travel_planner.config.settings")
        assert module.Settings is not None

    def test_missing_credentials_are_not_an_error(self) -> None:
        settings = _settings(llm_provider=LLMProvider.APMIX, llm_api_key="", tavily_api_key="")
        assert settings.has_llm_credentials is False
        assert settings.has_tavily_credentials is False

    def test_helpers_raise_only_when_called(self) -> None:
        from travel_planner.errors import LLMConfigurationError

        settings = _settings(llm_api_key="", tavily_api_key="")
        with pytest.raises(LLMConfigurationError):
            settings.require_llm_credentials()
        with pytest.raises(LLMConfigurationError):
            settings.require_tavily_credentials()

    def test_mock_provider_is_offline(self) -> None:
        assert _settings(llm_provider=LLMProvider.MOCK).is_offline is True

    def test_secrets_are_masked_in_redacted_dict(self) -> None:
        settings = _settings(llm_api_key="abc123", stripe_secret_key="sk_live_x")
        redacted = settings.redacted()
        assert "abc123" not in str(redacted)
        assert "sk_live_x" not in str(redacted)
        assert "abc123" not in repr(settings.llm_api_key)

    def test_extraction_model_falls_back_to_main_model(self) -> None:
        assert _settings(llm_model="m1", llm_extraction_model="").effective_extraction_model == "m1"
        assert (
            _settings(llm_model="m1", llm_extraction_model="m2").effective_extraction_model == "m2"
        )

    def test_csv_provider_chain_is_parsed(self) -> None:
        settings = _settings(
            hotels_providers="scraper_a,curated,estimator",
            transport_providers="curated",
        )
        assert settings.hotels_providers == ["scraper_a", "curated", "estimator"]
        assert settings.transport_providers == ["curated"]

    def test_cached_settings_can_be_reloaded(self) -> None:
        first = get_settings()
        assert get_settings() is first, "get_settings must be cached"
        reloaded = reload_settings()
        assert reloaded is not first, "reload_settings must clear the cache"
        assert get_settings() is reloaded

    def test_invalid_numeric_bounds_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            _settings(llm_temperature=5.0)
        with pytest.raises(ValueError):
            _settings(llm_max_tokens=0)


class TestRegionProfiles:
    def test_iran_profile_is_jalali_rtl_toman(self) -> None:
        assert IRAN_PROFILE.calendar is CalendarSystem.JALALI
        assert IRAN_PROFILE.direction is TextDirection.RTL
        assert IRAN_PROFILE.default_currency is Currency.TOMAN
        assert IRAN_PROFILE.primary_language is Language.FA
        assert IRAN_PROFILE.uses_persian_digits is True

    def test_international_profile_is_gregorian_ltr_usd(self) -> None:
        assert INTERNATIONAL_PROFILE.calendar is CalendarSystem.GREGORIAN
        assert INTERNATIONAL_PROFILE.direction is TextDirection.LTR
        assert INTERNATIONAL_PROFILE.default_currency is Currency.USD
        assert INTERNATIONAL_PROFILE.primary_language is Language.EN

    @pytest.mark.parametrize(
        ("amount", "expected"),
        [
            (1_250_000, "1,250,000 تومان"),
            (500, "500 تومان"),
        ],
    )
    def test_toman_is_always_labelled(self, amount: float, expected: str) -> None:
        assert IRAN_PROFILE.label_currency(amount) == expected

    def test_irr_is_labelled_distinctly(self) -> None:
        rendered = IRAN_PROFILE.label_currency(1_000_000, Currency.IRR)
        assert "ریال" in rendered
        assert "تومان" not in rendered

    def test_foreign_currency_uses_code(self) -> None:
        assert INTERNATIONAL_PROFILE.label_currency(45.6) == "46 USD"

    def test_unknown_capability_chain_is_empty_not_an_error(self) -> None:
        assert IRAN_PROFILE.chain_for("does_not_exist") == ()

    def test_get_profile_covers_both_regions(self) -> None:
        assert get_profile(Region.IRAN) is IRAN_PROFILE
        assert get_profile(Region.INTERNATIONAL) is INTERNATIONAL_PROFILE

    def test_every_capability_has_a_chain_in_both_profiles(self) -> None:
        capabilities = set(IRAN_PROFILE.provider_chains)
        assert capabilities == set(INTERNATIONAL_PROFILE.provider_chains)
        for profile in (IRAN_PROFILE, INTERNATIONAL_PROFILE):
            for capability, chain in profile.provider_chains.items():
                assert chain, f"{capability} has an empty chain in {profile.region}"
