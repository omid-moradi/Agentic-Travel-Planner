"""Unit tests for the typed schemas."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from travel_planner.config.regions import Currency
from travel_planner.config.settings import Language, Region
from travel_planner.schemas import (
    Coordinates,
    DataStatus,
    DayActivity,
    DayPlan,
    Finding,
    Itinerary,
    OpeningHours,
    PlaceInfo,
    PriceEstimate,
    Source,
    TransportMode,
    TravelState,
    TripRequest,
    ValidationIssue,
)


def _request(**kwargs: object) -> TripRequest:
    defaults: dict[str, object] = {
        "raw_input": "test",
        "region": Region.IRAN,
        "language": Language.FA,
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)  # type: ignore[arg-type]


def _place(name: str = "Test Place", lat: float = 35.0, lon: float = 51.0) -> PlaceInfo:
    return PlaceInfo(
        name=name,
        place_type="attraction",
        coordinates=Coordinates(lat=lat, lon=lon),
        average_visit_duration_minutes=60,
    )


class TestCoordinates:
    def test_valid(self) -> None:
        c = Coordinates(lat=35.7, lon=51.4)
        assert c.lat == 35.7

    @pytest.mark.parametrize(
        ("lat", "lon"),
        [(91, 0), (-91, 0), (0, 181), (0, -181)],
    )
    def test_out_of_range_rejected(self, lat: float, lon: float) -> None:
        with pytest.raises(ValidationError):
            Coordinates(lat=lat, lon=lon)


class TestPriceEstimate:
    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PriceEstimate(amount=-1, currency=Currency.TOMAN, status=DataStatus.ESTIMATED)

    def test_status_is_required(self) -> None:
        price = PriceEstimate(amount=100, currency=Currency.TOMAN, status=DataStatus.CONFIRMED)
        assert price.status is DataStatus.CONFIRMED


class TestDayActivity:
    def test_hhmm_normalised(self) -> None:
        activity = DayActivity(place=_place(), start_time="9:5", end_time="10:05")
        assert activity.start_time == "09:05"

    @pytest.mark.parametrize("bad", ["25:00", "12:60", "12-30", "abc", "12:3:4"])
    def test_bad_time_rejected(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            DayActivity(place=_place(), start_time=bad, end_time="11:00")

    def test_empty_times_allowed(self) -> None:
        activity = DayActivity(place=_place(), start_time="", end_time="")
        assert activity.start_time == ""


class TestTripRequest:
    def test_defaults(self) -> None:
        request = _request()
        assert request.travelers == 1
        assert request.destinations == []
        assert request.start_date is None

    def test_travelers_bounds(self) -> None:
        with pytest.raises(ValidationError):
            _request(travelers=0)
        with pytest.raises(ValidationError):
            _request(travelers=51)

    def test_none_lists_become_empty(self) -> None:
        request = _request(destinations=None)  # type: ignore[arg-type]
        assert request.destinations == []

    def test_dates(self) -> None:
        request = _request(start_date=date(2026, 11, 1), duration_nights=3)
        assert request.start_date == date(2026, 11, 1)
        assert request.duration_nights == 3


class TestTravelState:
    def test_defaults_and_mutation(self) -> None:
        state = TravelState(request=_request())
        assert state.current_step == "start"
        assert state.repair_count == 0
        state.places_findings.append(
            Finding(category="places", summary="s", status=DataStatus.CONFIRMED)
        )
        assert len(state.places_findings) == 1

    def test_max_repair_loops(self) -> None:
        state = TravelState(request=_request(), max_repair_loops=5)
        assert state.max_repair_loops == 5


class TestFinding:
    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            Finding(category="c", summary="s", status=DataStatus.INFERRED, confidence=1.5)

    def test_unavailable_never_invents_data(self) -> None:
        finding = Finding(
            category="events",
            summary="not available",
            status=DataStatus.UNAVAILABLE,
        )
        assert finding.status is DataStatus.UNAVAILABLE


class TestOpeningHours:
    def test_all_days_default_empty(self) -> None:
        hours = OpeningHours()
        assert hours.monday == ""
        assert hours.always_open is False


class TestSource:
    def test_retrieved_at_defaults_to_now(self) -> None:
        source = Source(name="test")
        assert source.retrieved_at is not None


class TestValidationIssue:
    def test_severity_is_constrained(self) -> None:
        issue = ValidationIssue(
            severity="warning", category="budget", description="over"
        )
        assert issue.severity == "warning"
        with pytest.raises(ValidationError):
            ValidationIssue(severity="fatal", category="budget", description="x")  # type: ignore[arg-type]


class TestItineraryIntegration:
    def test_full_itinerary_validates(self) -> None:
        place = _place()
        day = DayPlan(
            day_number=1,
            date=date(2026, 11, 1),
            city="Tehran",
            activities=[
                DayActivity(place=place, start_time="09:00", end_time="10:00")
            ],
            daily_budget=PriceEstimate(
                amount=100, currency=Currency.TOMAN, status=DataStatus.ESTIMATED
            ),
        )
        itinerary = Itinerary(days=[day])
        assert itinerary.days[0].city == "Tehran"
        assert itinerary.days[0].activities[0].transport_to_next is None

    def test_transport_mode_enum(self) -> None:
        assert TransportMode.WALK.value == "walk"
