from enum import Enum

from pydantic import BaseModel


class ResearchStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    DATASET_DISCOVERY = "dataset_discovery"
    DATASET_EVALUATION = "dataset_evaluation"
    ANALYSIS = "analysis"
    PATHWAYS = "pathways"
    LITERATURE = "literature"
    SCIENTIFIC_REVIEW = "scientific_review"
    REPORT = "report"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchJob(BaseModel):
    research_id: str
    question: str
    status: ResearchStatus = ResearchStatus.QUEUED
    message: str = "Research investigation created."