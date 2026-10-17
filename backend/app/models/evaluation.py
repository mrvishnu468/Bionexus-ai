from enum import Enum

from pydantic import BaseModel, Field


class DatasetSuitability(str, Enum):
    RECOMMENDED = "recommended"
    CONDITIONAL = "conditional"
    NOT_RECOMMENDED = "not_recommended"


class DatasetAssayType(str, Enum):
    BULK_RNA_SEQ = "bulk_rna_seq"
    SINGLE_CELL_RNA_SEQ = "single_cell_rna_seq"
    SINGLE_NUCLEUS_RNA_SEQ = "single_nucleus_rna_seq"
    OTHER = "other"
    UNKNOWN = "unknown"


class DatasetEvaluation(BaseModel):
    accession: str
    suitability: DatasetSuitability
    assay_type: DatasetAssayType
    score: int
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    relevance_score: int = 0
    readiness_score: int = 0
    suitability_score: int = 0
    unknowns: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, int] = Field(default_factory=dict)