from pydantic import BaseModel


class StudySummary(BaseModel):
    accession: str
    title: str | None = None
    abstract: str | None = None
    organism: str | None = None
    experiment_count: int = 0
    sample_count: int = 0
    run_count: int = 0
    experiments: list[str] = []