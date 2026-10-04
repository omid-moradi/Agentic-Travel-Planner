"""Evaluation scenarios - fixed, reproducible, offline.

25 scenarios covering the master prompt's demanded spread: Iran domestic,
international, budget cuts, incomplete requests, multi-city, live mode and
edge cases. Each scenario is a typed request plus expectations the runner
checks. The LLM is always ``mock`` so results are reproducible (ADR-009).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Expectations(BaseModel):
    """What a good plan must satisfy for this scenario."""

    valid: bool = True
    min_days: int = 1
    max_days: int = 90
    cities: list[str] = Field(default_factory=list)
    # A budget this tight must produce a warning, not a silent success.
    expect_budget_warning: bool = False
    # Incomplete requests: unknown cities must fall back safely, not crash.
    expect_safe_fallback: bool = False


class Scenario(BaseModel):
    name: str
    description: str
    category: Literal[
        "iran_domestic", "international", "budget", "incomplete",
        "multi_city", "live_mode", "edge_case",
    ]
    request: dict[str, object]
    expectations: Expectations


def _req(**kwargs: object) -> dict[str, object]:
    defaults: dict[str, object] = {"region": "iran", "language": "fa"}
    defaults.update(kwargs)
    return defaults


SCENARIOS: list[Scenario] = [
    # ------------------------------------------------------- Iran domestic
    Scenario(
        name="tehran_shiraz_3n",
        description="The canonical golden path: 3 nights Tehran -> Shiraz",
        category="iran_domestic",
        request=_req(
            request="Tehran to Shiraz, 3 nights",
            destinations=["Tehran", "Shiraz"],
            duration_nights=3,
            start_date=date(2026, 11, 1),
        ),
        expectations=Expectations(min_days=3, max_days=3, cities=["tehran", "shiraz"]),
    ),
    Scenario(
        name="tehran_only_1n",
        description="Single city, single night",
        category="iran_domestic",
        request=_req(request="One night in Tehran", destinations=["Tehran"], duration_nights=1),
        expectations=Expectations(min_days=1, max_days=1, cities=["tehran"]),
    ),
    Scenario(
        name="shiraz_5n_summer",
        description="Longer stay in one city, summer season",
        category="iran_domestic",
        request=_req(
            request="Five nights in Shiraz in July",
            destinations=["Shiraz"],
            duration_nights=5,
            start_date=date(2026, 7, 10),
        ),
        expectations=Expectations(min_days=5, max_days=5, cities=["shiraz"]),
    ),
    Scenario(
        name="tehran_winter_week",
        description="A full week in Tehran in winter",
        category="iran_domestic",
        request=_req(
            request="A week in Tehran in January",
            destinations=["Tehran"],
            duration_nights=7,
            start_date=date(2027, 1, 5),
        ),
        expectations=Expectations(min_days=7, max_days=7, cities=["tehran"]),
    ),
    Scenario(
        name="shiraz_group_of_8",
        description="Large travel group (8 people)",
        category="iran_domestic",
        request=_req(
            request="Shiraz for a group of 8",
            destinations=["Shiraz"],
            duration_nights=2,
            travelers=8,
        ),
        expectations=Expectations(min_days=2, max_days=2, cities=["shiraz"]),
    ),
    Scenario(
        name="nowruz_peak",
        description="Nowruz peak-season domestic trip (workload caps must hold)",
        category="iran_domestic",
        request=_req(
            request="Nowruz trip to Shiraz",
            destinations=["Shiraz"],
            duration_nights=4,
            start_date=date(2027, 3, 20),
        ),
        expectations=Expectations(min_days=4, max_days=4, cities=["shiraz"]),
    ),
    # ---------------------------------------------------------- multi-city
    Scenario(
        name="multi_city_5n",
        description="Five nights split across both fixture cities",
        category="multi_city",
        request=_req(
            request="Tehran then Shiraz, 5 nights total",
            destinations=["Tehran", "Shiraz"],
            duration_nights=5,
        ),
        expectations=Expectations(min_days=5, max_days=5, cities=["tehran", "shiraz"]),
    ),
    Scenario(
        name="multi_city_1n_each",
        description="One night per city - the tightest split",
        category="multi_city",
        request=_req(
            request="Tehran and Shiraz, one night each",
            destinations=["Tehran", "Shiraz"],
            duration_nights=2,
        ),
        expectations=Expectations(min_days=2, max_days=2, cities=["tehran", "shiraz"]),
    ),
    Scenario(
        name="multi_city_uneven_4n",
        description="Uneven split: 4 nights, remainder goes to the first city",
        category="multi_city",
        request=_req(
            request="Mostly Tehran, then Shiraz - 4 nights",
            destinations=["Tehran", "Shiraz"],
            duration_nights=4,
        ),
        expectations=Expectations(min_days=4, max_days=4),
    ),
    # --------------------------------------------------------------- budget
    Scenario(
        name="budget_impossible_100",
        description="A 100-Toman budget must produce a warning, never silence",
        category="budget",
        request=_req(
            request="Shiraz weekend",
            destinations=["Shiraz"],
            duration_nights=2,
            budget_total=100.0,
        ),
        expectations=Expectations(min_days=2, max_days=2, expect_budget_warning=True),
    ),
    Scenario(
        name="budget_tight_2m",
        description="A tight but plausible budget",
        category="budget",
        request=_req(
            request="Tehran for 2 nights",
            destinations=["Tehran"],
            duration_nights=2,
            budget_total=2_000_000.0,
        ),
        expectations=Expectations(min_days=2, max_days=2, expect_budget_warning=True),
    ),
    Scenario(
        name="budget_generous",
        description="A generous budget should not warn",
        category="budget",
        request=_req(
            request="Tehran for 1 night",
            destinations=["Tehran"],
            duration_nights=1,
            budget_total=500_000_000.0,
        ),
        expectations=Expectations(min_days=1, max_days=1, expect_budget_warning=False),
    ),
    # ------------------------------------------------------------ incomplete
    Scenario(
        name="incomplete_unknown_city",
        description="An unknown city must fall back safely to Tehran",
        category="incomplete",
        request=_req(request="Trip to Atlantis", destinations=["Atlantis"], duration_nights=2),
        expectations=Expectations(min_days=2, max_days=2, expect_safe_fallback=True),
    ),
    Scenario(
        name="incomplete_no_cities",
        description="No destination at all - the safe default applies",
        category="incomplete",
        request=_req(request="Somewhere nice please", destinations=[], duration_nights=1),
        expectations=Expectations(min_days=1, max_days=1, expect_safe_fallback=True),
    ),
    Scenario(
        name="incomplete_no_nights",
        description="No duration: one night per city is the documented default",
        category="incomplete",
        request=_req(request="Tehran sometime", destinations=["Tehran"]),
        expectations=Expectations(min_days=1, max_days=1),
    ),
    Scenario(
        name="incomplete_past_date",
        description="A start date in the past still plans deterministically",
        category="incomplete",
        request=_req(
            request="Tehran last month",
            destinations=["Tehran"],
            duration_nights=1,
            start_date=date(2020, 1, 1),
        ),
        expectations=Expectations(min_days=1, max_days=1),
    ),
    Scenario(
        name="incomplete_far_future",
        description="A date far in the future (weather will be honestly unavailable)",
        category="incomplete",
        request=_req(
            request="Shiraz in 2030",
            destinations=["Shiraz"],
            duration_nights=2,
            start_date=date(2030, 5, 1),
        ),
        expectations=Expectations(min_days=2, max_days=2),
    ),
    # --------------------------------------------------------- international
    Scenario(
        name="international_paris",
        description="International trip (fixture data applies; entry items are advisory)",
        category="international",
        request=_req(
            request="Weekend in Paris",
            region="international",
            language="en",
            destinations=["Tehran"],  # fixture coverage; region drives the profile
            duration_nights=2,
        ),
        expectations=Expectations(min_days=2, max_days=2),
    ),
    Scenario(
        name="international_english_output",
        description="English output for an international request",
        category="international",
        request=_req(
            request="City break, 2 nights",
            region="international",
            language="en",
            destinations=["Tehran"],
            duration_nights=2,
        ),
        expectations=Expectations(min_days=2, max_days=2),
    ),
    Scenario(
        name="international_mixed_currencies",
        description="International region with a USD budget",
        category="international",
        request=_req(
            request="Two nights, USD budget",
            region="international",
            language="en",
            destinations=["Tehran"],
            duration_nights=2,
            budget_total=1500.0,
        ),
        expectations=Expectations(min_days=2, max_days=2),
    ),
    # ------------------------------------------------------------- live mode
    Scenario(
        name="live_mode_rain_reason",
        description="Live-mode re-plan with the rain reason is accepted and traced",
        category="live_mode",
        request=_req(request="Shiraz live", destinations=["Shiraz"], duration_nights=1),
        expectations=Expectations(min_days=1, max_days=1),
    ),
    Scenario(
        name="live_mode_tired_reason",
        description="Live-mode re-plan with the tired reason",
        category="live_mode",
        request=_req(request="Tehran live", destinations=["Tehran"], duration_nights=1),
        expectations=Expectations(min_days=1, max_days=1),
    ),
    # ------------------------------------------------------------ edge cases
    Scenario(
        name="edge_long_trip_30n",
        description="A 30-night trip - day distribution must hold",
        category="edge_case",
        request=_req(
            request="A month in Tehran and Shiraz",
            destinations=["Tehran", "Shiraz"],
            duration_nights=30,
        ),
        expectations=Expectations(min_days=30, max_days=30),
    ),
    Scenario(
        name="edge_max_travelers",
        description="The maximum allowed travelers (50)",
        category="edge_case",
        request=_req(
            request="Shiraz for a company outing",
            destinations=["Shiraz"],
            duration_nights=1,
            travelers=50,
        ),
        expectations=Expectations(min_days=1, max_days=1),
    ),
    Scenario(
        name="edge_one_activity_day",
        description="A one-night trip with minimal data - still valid",
        category="edge_case",
        request=_req(request="Quick stopover in Tehran", destinations=["Tehran"], duration_nights=1),
        expectations=Expectations(min_days=1, max_days=1),
    ),
]
