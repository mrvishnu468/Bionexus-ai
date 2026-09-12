from pydantic import BaseModel


class SRADataset(BaseModel):
    accession: str
    study_accession: str | None = None
    title: str | None = None
    organism: str | None = None
    library_strategy: str | None = None
    library_source: str | None = None
    description: str | None = None
    sample_count: int | None = None
    run_count: int | None = None
    study_title: str | None = None
    study_abstract: str | None = None
    experiment_type: str | None = None
    samples: list[dict] = []