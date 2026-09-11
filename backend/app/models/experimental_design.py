from pydantic import BaseModel


class ExperimentalGroup(BaseModel):
    name: str
    sample_count: int


class ExperimentalDesign(BaseModel):
    groups: list[ExperimentalGroup]
    has_biological_replicates: bool
    has_control_group: bool
    metadata_complete: bool
    notes: list[str] = []