
from enum import Enum

from pydantic import BaseModel, Field


class IntentFieldStatus(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"

class IntentReviewStatus(str, Enum):
    PROPOSED = "proposed"
    NEEDS_CLARIFICATION = "needs_clarification"
    CONFIRMED = "confirmed"



class IntentField(BaseModel):
    value: str | None = None
    status: IntentFieldStatus = IntentFieldStatus.UNKNOWN
    evidence: list[str] = Field(default_factory=list)


class ResearchIntent(BaseModel):
    original_question: str
    review_status: IntentReviewStatus = IntentReviewStatus.PROPOSED

    research_goal: IntentField = Field(default_factory=IntentField)
    disease: IntentField = Field(default_factory=IntentField)
    gene: IntentField = Field(default_factory=IntentField)
    organism: IntentField = Field(default_factory=IntentField)
    tissue: IntentField = Field(default_factory=IntentField)
    assay_type: IntentField = Field(default_factory=IntentField)
    analysis_goal: IntentField = Field(default_factory=IntentField)
    comparison: IntentField = Field(default_factory=IntentField)

    constraints: list[str] = Field(default_factory=list)

    clarification_required: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
