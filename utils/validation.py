from pydantic import BaseModel, Field, field_validator
from typing import List, Literal


class Source(BaseModel):
    """Represents a single source for a piece of information."""
    name: str = Field(..., description="Name of the source website or organization (e.g., 'Snapp (FA)')")
    url: str = Field(..., description="The full URL of the source.")

class Finding(BaseModel):
    """Represents a single finding on a specific topic."""
    topic: str = Field(..., description="The topic of the finding, e.g., 'Airport Transfers'")
    bullets: List[str] = Field(..., description="A list of concise, factual points about the topic.")
    sources: List[Source]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0 on the accuracy of the information.")

class ResearchReport(BaseModel):
    """The complete, structured research report for a travel destination."""
    currency: Literal["TOMAN"] = Field(default="TOMAN", description="The currency for all costs must be TOMAN.")
    findings: List[Finding]
    risks: List[str] = Field(..., description="A list of potential risks, from seasonal issues to common scams.")
    verification: List[str] = Field(..., description="A list of suggestions on how to verify critical information.")

class ItineraryDay(BaseModel):
    """Represents the plan for a single day of the trip."""
    date: str = Field(..., description="Date of the itinerary day in 'YYYY-MM-DD' format.")
    summary: str = Field(..., description="A short, one-sentence summary of the day's activities.")
    morning: List[str]
    afternoon: List[str]
    evening: List[str]
    est_cost_toman: int = Field(..., description="Estimated cost for the day in whole Toman (integer).")

class ItineraryPlan(BaseModel):
    """The complete, day-by-day itinerary plan."""
    currency: Literal["TOMAN"] = Field(default="TOMAN")
    overview: str = Field(..., description="A brief overview of the entire trip, written in Persian.")
    days: List[ItineraryDay]
    total_est_cost_toman: int

    @field_validator('days')
    def must_have_at_least_one_day(cls, v):
        """
        Validator for the `days` field in `ItineraryPlan`.
        Verifies that the `days` field has at least one day in the itinerary.
        If the list is empty, it raises a ValueError with a helpful message.
        """
        if not v:
            raise ValueError('Itinerary must have at least one day.')
        return v