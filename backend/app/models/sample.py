from pydantic import BaseModel


class SRASample(BaseModel):
    accession: str
    title: str | None = None
    organism: str | None = None
    attributes: dict[str, str] = {}
    experiment_accession: str | None = None
    study_accession: str | None = None