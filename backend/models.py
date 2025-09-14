from pydantic import BaseModel, Field
from typing import List, Optional


class BusinessInput(BaseModel):
    area_sqm: float = Field(ge=0)
    seats: int = Field(ge=0)
    uses_gas: bool
    serves_meat: bool
    offers_delivery: bool


class ParseResponse(BaseModel):
    total_requirements: int
    sample: List[dict]


class SectionNode(BaseModel):
    id: str  # e.g. "1", "1.2", "1.2.3"
    level: int  # 1, 2 or 3
    text: str
    # Short heading/title extracted from the body for display and AI prompts
    title: Optional[str] = None
    # Context of numbering:
    # - "normal" (default)
    # - "annex4" (נספחים under chapter 4)
    # - "annex5" (sub-annex after נספח 1 (לנספח א'))
    context: Optional[str] = None
    # Group level label for annexes, e.g. "4.1", "4.2", "4.3" or "5.1"...
    group_level: Optional[str] = None
    min_area_sqm: Optional[float] = None
    max_area_sqm: Optional[float] = None
    min_seats: Optional[int] = None
    max_seats: Optional[int] = None
    requires_gas: Optional[bool] = None
    serves_meat: Optional[bool] = None
    offers_delivery: Optional[bool] = None
    children: List["SectionNode"] = Field(default_factory=list)


# Rebuild forward refs for recursive model
SectionNode.model_rebuild()


class AIReportRequest(BaseModel):
    business: BusinessInput
    matched: List[dict]
    language: Optional[str] = Field(default="he")


class AIReportResponse(BaseModel):
    report: str


class AIReportStructureRequest(BaseModel):
    business: BusinessInput
    nodes: List[SectionNode]
    language: Optional[str] = Field(default="he")



