"""Typed data schemas shared across the agentic workflow.

Every finding that references an external fact carries a status:

  confirmed   - retrieved from a known, recent source
  estimated   - computed using a documented method
  inferred    - model guessed with explicit uncertainty
  unavailable - system tried and could not obtain the value

No value ever appears without one of these four states (ADR-009).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

from travel_planner.config.regions import Currency
from travel_planner.config.settings import Language, Region


class DataStatus(StrEnum):
    """Provenance of a piece of information."""

    CONFIRMED = "confirmed"
    ESTIMATED = "estimated"
    INFERRED = "inferred"
    UNAVAILABLE = "unavailable"


class TripStyle(StrEnum):
    CULTURAL = "cultural"
    NATURE = "nature"
    FOODIE = "foodie"
    SHOPPING = "shopping"
    ADVENTURE = "adventure"
    RELAXED = "relaxed"
    FAMILY = "family"
    BUSINESS = "business"


class AccommodationType(StrEnum):
    HOTEL = "hotel"
    HOSTEL = "hostel"
    GUESTHOUSE = "guesthouse"
    APARTMENT = "apartment"
    HOMESTAY = "homestay"


class TransportMode(StrEnum):
    WALK = "walk"
    BIKE = "bike"
    BUS = "bus"
    METRO = "metro"
    TAXI = "taxi"
    RIDE_SHARE = "ride_share"
    TRAIN = "train"
    FLIGHT = "flight"
    CAR_RENTAL = "car_rental"


class Coordinates(BaseModel):
    """Geographic location."""

    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]


class Source(BaseModel):
    """Attribution for an external fact."""

    name: str
    url: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.now)


class OpeningHours(BaseModel):
    """Weekly schedule for a venue."""

    always_open: bool = False
    monday: str = ""
    tuesday: str = ""
    wednesday: str = ""
    thursday: str = ""
    friday: str = ""
    saturday: str = ""
    sunday: str = ""
    note: str = ""


class PlaceInfo(BaseModel):
    """A point of interest, hotel, restaurant or transport hub."""

    name: str
    place_type: str
    address: str = ""
    coordinates: Coordinates | None = None
    description: str = ""
    opening_hours: OpeningHours | None = None
    average_visit_duration_minutes: int | None = None
    rating: float | None = None
    price_level: Literal[1, 2, 3, 4] | None = None
    status: DataStatus = DataStatus.CONFIRMED
    source: Source | None = None


class PriceEstimate(BaseModel):
    """A cost with a currency, a status and an optional source."""

    amount: Annotated[float, Field(ge=0)]
    currency: Currency
    status: DataStatus
    source: Source | None = None
    note: str = ""


class RouteSegment(BaseModel):
    """One leg of a journey between two places."""

    origin: PlaceInfo
    destination: PlaceInfo
    mode: TransportMode
    distance_km: Annotated[float, Field(ge=0)]
    duration_minutes: Annotated[int, Field(ge=0)]
    cost: PriceEstimate | None = None
    departure_time: str = ""
    arrival_time: str = ""
    notes: list[str] = Field(default_factory=list)


class DayActivity(BaseModel):
    """One activity or venue visit."""

    place: PlaceInfo
    start_time: str
    end_time: str
    transport_to_next: RouteSegment | None = None
    cost: PriceEstimate | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("start_time", "end_time")
    @classmethod
    def check_time_format(cls, value: str) -> str:
        if value == "":
            return value
        parts = value.split(":")
        if len(parts) != 2:
            msg = f"Time must be HH:MM, got {value!r}"
            raise ValueError(msg)
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except ValueError as exc:
            msg = f"Time must be HH:MM, got {value!r}"
            raise ValueError(msg) from exc
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            msg = f"Time must be HH:MM with 0<=HH<=23 and 0<=MM<=59, got {value!r}"
            raise ValueError(msg)
        return f"{hour:02d}:{minute:02d}"


class DayPlan(BaseModel):
    """One day inside an itinerary."""

    day_number: Annotated[int, Field(ge=1)]
    date: date
    city: str
    accommodation: PlaceInfo | None = None
    activities: list[DayActivity] = Field(default_factory=list)
    meals: list[PlaceInfo] = Field(default_factory=list)
    daily_budget: PriceEstimate | None = None
    weather_forecast: str = ""
    notes: list[str] = Field(default_factory=list)


class TripRequest(BaseModel):
    """Parsed, typed user intent - the single input to the graph."""

    raw_input: str
    region: Region
    language: Language
    destinations: list[str] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    duration_nights: int | None = None
    budget_total: float | None = None
    budget_currency: Currency | None = None
    travelers: Annotated[int, Field(ge=1, le=50)] = 1
    styles: list[TripStyle] = Field(default_factory=list)
    accommodation_types: list[AccommodationType] = Field(default_factory=list)
    must_visit: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)

    @field_validator(
        "destinations",
        "styles",
        "accommodation_types",
        "must_visit",
        "avoid",
        "accessibility_needs",
        "dietary_restrictions",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        return value  # type: ignore[no-any-return]


class TravelState(BaseModel):
    """LangGraph state, checkpointed and typed.

    Nodes append to lists; the supervisor and critic read everything.
    No node overwrites another's work.
    """

    request: TripRequest
    clarifications: list[str] = Field(default_factory=list)
    places_findings: list[Finding] = Field(default_factory=list)
    accommodation_findings: list[Finding] = Field(default_factory=list)
    transport_findings: list[Finding] = Field(default_factory=list)
    restaurants_findings: list[Finding] = Field(default_factory=list)
    weather_findings: list[Finding] = Field(default_factory=list)
    events_findings: list[Finding] = Field(default_factory=list)
    culture_findings: list[Finding] = Field(default_factory=list)
    safety_findings: list[Finding] = Field(default_factory=list)
    requirements_findings: list[Finding] = Field(default_factory=list)
    itinerary: Itinerary | None = None
    itinerary_drafts: list[Itinerary] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    is_valid: bool = False
    messages: list[dict[str, str]] = Field(default_factory=list)
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    current_step: str = "start"
    repair_count: int = 0
    max_repair_loops: int = 2


class Itinerary(BaseModel):
    """The complete day-by-day plan."""

    days: list[DayPlan]
    total_cost: PriceEstimate | None = None
    route_map_url: str | None = None


class Finding(BaseModel):
    """One research output from a node, with provenance."""

    category: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    status: DataStatus
    source: Source | None = None
    confidence: Annotated[float, Field(ge=0, le=1)] = 1.0


class ValidationIssue(BaseModel):
    """One problem found by the validator."""

    severity: Literal["error", "warning", "info"]
    category: str
    description: str
    affected_day: int | None = None
    affected_activity: str | None = None


# Rebuild forward refs (Finding/Itinerary referenced before definition in TravelState)
TravelState.model_rebuild()

