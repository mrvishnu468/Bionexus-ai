from pydantic import BaseModel


class SRARun(BaseModel):
    accession: str
    experiment_accession: str | None = None
    sample_accession: str | None = None


class SRASample(BaseModel):
    accession: str
    title: str | None = None
    organism: str | None = None
    attributes: dict[str, str] = {}
    experiment_accession: str | None = None
    study_accession: str | None = None
    runs: list[SRARun] = []


class SRAExperiment(BaseModel):
    accession: str
    title: str | None = None
    study_accession: str | None = None
    organism: str | None = None
    samples: list[SRASample] = []


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
    experiments: list[SRAExperiment] = []
    samples: list[SRASample] = []