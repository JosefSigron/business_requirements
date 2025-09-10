from pydantic import BaseModel, Field
from typing import List, Optional


class Requirement(BaseModel):
    id: str
    title: str
    description: str
    min_area_sqm: Optional[float] = None
    max_area_sqm: Optional[float] = None
    min_seats: Optional[int] = None
    max_seats: Optional[int] = None
    requires_gas: Optional[bool] = None
    serves_meat: Optional[bool] = None
    offers_delivery: Optional[bool] = None
    category: Optional[str] = None


class BusinessInput(BaseModel):
    area_sqm: float = Field(ge=0)
    seats: int = Field(ge=0)
    uses_gas: bool
    serves_meat: bool
    offers_delivery: bool


class MatchResponse(BaseModel):
    total_requirements: int
    matched_count: int
    matched: List[Requirement]


class ParseResponse(BaseModel):
    total_requirements: int
    sample: List[Requirement]


class AIReportRequest(BaseModel):
    business: BusinessInput
    matched: List[Requirement]
    language: Optional[str] = Field(default="he")


class AIReportResponse(BaseModel):
    report: str



