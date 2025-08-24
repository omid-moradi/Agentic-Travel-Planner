from pydantic import BaseModel, Field
from typing import List

class Source(BaseModel):
    name: str = Field(..., description="Name of the source website or organization")
    url: str = Field(..., description="URL of the source")

class Finding(BaseModel):
    topic: str
    bullets: List[str]
    sources: List[Source]
    confidence: float

class ResearchReport(BaseModel):
    currency: str = Field(default="TOMAN")
    findings: List[Finding]


import outlines
from utils.validation import ResearchReport

model = outlines.models.openai("gemini-1.5-flash", api_key="...")
guided_model = outlines.generate.json(model, ResearchReport)

report_object = guided_model("Research Mashhad for a trip...")