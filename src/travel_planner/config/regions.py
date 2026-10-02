"""Market region profiles.

A ``RegionProfile`` is config-driven and decides, per trip: providers, currency, calendar,
language and data sources. No module may assume a single global provider set.

See ``docs/decisions.md`` and section 6 of ``plan-mode-cline.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from travel_planner.config.settings import Language, Region


class Currency(StrEnum):
    """Currencies the product can present.

    ``TOMAN`` is always labelled explicitly; 1 Toman = 10 IRR.
    """

    IRR = "IRR"
    TOMAN = "TOMAN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    TRY = "TRY"
    AED = "AED"


class CalendarSystem(StrEnum):
    GREGORIAN = "gregorian"
    JALALI = "jalali"


class TextDirection(StrEnum):
    LTR = "ltr"
    RTL = "rtl"


#: Currencies a user may toggle between for a given trip.
TOMAN_IRR_PAIR: tuple[Currency, Currency] = (Currency.TOMAN, Currency.IRR)


@dataclass(frozen=True, slots=True)
class RegionProfile:
    """Everything that varies by market, resolved once per trip."""

    region: Region
    default_currency: Currency
    allowed_currencies: tuple[Currency, ...]
    calendar: CalendarSystem
    primary_language: Language
    fallback_language: Language
    direction: TextDirection
    uses_persian_digits: bool
    #: Provider chain per capability. Empty string means "no provider configured".
    provider_chains: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: Human-readable notes surfaced in the UI and in the agent prompts.
    notes: tuple[str, ...] = ()

    def chain_for(self, capability: str) -> tuple[str, ...]:
        """Ordered provider chain for a capability (empty when unconfigured)."""
        return self.provider_chains.get(capability, ())

    def label_currency(self, amount: float, currency: Currency | None = None) -> str:
        """Render an amount with its currency, always spelled out.

        Toman is never abbreviated to a bare number, because IRR/Toman confusion is a
        real and common error for Iranian travellers.
        """
        chosen = currency or self.default_currency
        rounded = round(amount)
        if chosen is Currency.TOMAN:
            return f"{rounded:,} تومان"
        if chosen is Currency.IRR:
            return f"{rounded:,} ریال"
        return f"{rounded:,} {chosen.value}"


IRAN_PROFILE = RegionProfile(
    region=Region.IRAN,
    default_currency=Currency.TOMAN,
    allowed_currencies=(Currency.TOMAN, Currency.IRR, Currency.USD, Currency.EUR),
    calendar=CalendarSystem.JALALI,
    primary_language=Language.FA,
    fallback_language=Language.EN,
    direction=TextDirection.RTL,
    uses_persian_digits=True,
    provider_chains={
        "places": ("fixture", "curated"),
        "hotels": ("curated", "estimator"),
        "transport": ("curated", "estimator"),
        "restaurants": ("curated", "estimator"),
        "ride_fare": ("estimator",),
        "weather": ("open_meteo",),
        "currency": ("exchangerate_host",),
        "routes": ("osrm",),
        "geocode": ("nominatim",),
        "events": ("fixture", "curated"),
    },
    notes=(
        "Costs are presented in Toman by default; the IRR/Toman toggle is always labelled.",
        "Dates are shown in both Jalali (Shamsi) and Gregorian.",
        "Prayer/closing times and local holidays affect opening hours.",
        "Nowruz and peak seasons raise demand and prices - flag them explicitly.",
    ),
)

INTERNATIONAL_PROFILE = RegionProfile(
    region=Region.INTERNATIONAL,
    default_currency=Currency.USD,
    allowed_currencies=(Currency.USD, Currency.EUR, Currency.GBP, Currency.TRY, Currency.AED),
    calendar=CalendarSystem.GREGORIAN,
    primary_language=Language.EN,
    fallback_language=Language.FA,
    direction=TextDirection.LTR,
    uses_persian_digits=False,
    provider_chains={
        "places": ("fixture", "curated"),
        "hotels": ("curated", "estimator"),
        "transport": ("curated", "estimator"),
        "restaurants": ("curated", "estimator"),
        "ride_fare": ("estimator",),
        "weather": ("open_meteo",),
        "currency": ("exchangerate_host",),
        "routes": ("osrm",),
        "geocode": ("nominatim",),
        "events": ("fixture", "curated"),
    },
    notes=(
        "Entry requirements (visa, passport validity, insurance) must be sourced and dated.",
        "City-break itineraries are walking-first unless the user asks otherwise.",
        "Multi-city trips are supported; transport between cities is an explicit leg.",
    ),
)

PROFILES: dict[Region, RegionProfile] = {
    Region.IRAN: IRAN_PROFILE,
    Region.INTERNATIONAL: INTERNATIONAL_PROFILE,
}


def get_profile(region: Region) -> RegionProfile:
    """Return the profile for a region. Raises for an unknown region."""
    try:
        return PROFILES[region]
    except KeyError as exc:  # pragma: no cover - defensive
        msg = f"No region profile registered for {region!r}"
        raise KeyError(msg) from exc
