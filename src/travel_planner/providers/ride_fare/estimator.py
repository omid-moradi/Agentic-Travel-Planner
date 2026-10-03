"""Ride-fare estimator - a calibrated formula, never a private endpoint probe.

The master prompt is explicit: do **not** reverse-engineer or call private app
endpoints (Snapp/Tapsi etc.). Instead, fares are estimated from route distance
and time using a per-city calibrated formula, and the result is always labelled
``estimated`` with the basis documented.

Formula::

    fare = base + per_km * distance + per_minute * minutes, then x time-of-day

Calibration data lives in an editable dataset below; real fare samples can be
submitted through an admin UI in a later phase to tighten the coefficients.
"""

from __future__ import annotations

from travel_planner.config.regions import Currency
from travel_planner.schemas import DataStatus, PriceEstimate

#: Per-city calibrated coefficients in Toman (documented heuristic, editable).
_CITY_TARIFFS: dict[str, dict[str, float]] = {
    "tehran": {"base": 35_000.0, "per_km": 7_500.0, "per_minute": 1_500.0},
    "shiraz": {"base": 25_000.0, "per_km": 6_000.0, "per_minute": 1_200.0},
    "isfahan": {"base": 25_000.0, "per_km": 6_500.0, "per_minute": 1_300.0},
}

#: Fallback when a city is not calibrated yet.
_DEFAULT_TARIFF = {"base": 30_000.0, "per_km": 7_000.0, "per_minute": 1_400.0}

#: Multipliers by hour of day (peak demand). Keys are hour ranges.
_TIME_MULTIPLIERS = [
    ((0, 5), 0.9),    # night, quiet
    ((5, 7), 1.0),    # early morning
    ((7, 9), 1.3),    # morning rush
    ((9, 12), 1.05),
    ((12, 14), 1.0),
    ((14, 17), 1.1),
    ((17, 20), 1.35),  # evening rush
    ((20, 24), 1.1),
]


class RideFareEstimator:
    """Estimate intra-city ride fares from a documented formula (ADR-006)."""

    name = "estimator_ride_fare"

    def __init__(self, hour_of_day: int | None = None) -> None:
        # ``hour_of_day`` is injectable for deterministic tests.
        self._hour = hour_of_day

    def estimate_fare(
        self, distance_km: float, duration_minutes: int, city: str
    ) -> PriceEstimate:
        tariff = _CITY_TARIFFS.get(city.strip().lower(), _DEFAULT_TARIFF)
        base = tariff["base"] + tariff["per_km"] * distance_km + tariff["per_minute"] * duration_minutes
        amount = round(base * self._time_multiplier())
        return PriceEstimate(
            amount=float(amount),
            currency=Currency.TOMAN,
            status=DataStatus.ESTIMATED,
            note=(
                f"estimated from {distance_km:.1f} km / {duration_minutes} min "
                f"using the calibrated {city.strip().lower()} tariff; "
                "actual app fare may differ"
            ),
        )

    def _time_multiplier(self) -> float:
        import datetime as _dt

        hour = self._hour if self._hour is not None else _dt.datetime.now().hour
        for (start, end), multiplier in _TIME_MULTIPLIERS:
            if start <= hour < end:
                return multiplier
        return 1.0


#: Cities with calibration data, surfaced for the admin UI (later phase).
CALIBRATED_CITIES: tuple[str, ...] = tuple(sorted(_CITY_TARIFFS))
