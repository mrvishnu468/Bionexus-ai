from enum import Enum

from pydantic import BaseModel


class GroupDetectionStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANDIDATE = "candidate"
    UNKNOWN = "unknown"


class DetectedGroup(BaseModel):
    name: str
    sample_accessions: list[str]
    evidence: list[str]
    confidence: float


class GroupDetectionResult(BaseModel):
    status: GroupDetectionStatus
    groups: list[DetectedGroup]
    warnings: list[str]