from enum import Enum

from pydantic import BaseModel


class DatasetSuitability(str, Enum):
    RECOMMENDED = "recommended"
    CONDITIONAL = "conditional"
    NOT_RECOMMENDED = "not_recommended"


class DatasetEvaluation(BaseModel):
    accession: str
    suitability: DatasetSuitability
    score: int
    reasons: list[str]
    warnings: list[str]