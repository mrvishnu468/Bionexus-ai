from fastapi import APIRouter
from pydantic import BaseModel

from app.models.dataset import SRADataset
from app.models.evaluation import DatasetEvaluation
from app.services.study_dataset_discovery import (
    study_dataset_discovery,
)


router = APIRouter(
    prefix="/api/datasets",
    tags=["Datasets"],
)


class DatasetSearchRequest(BaseModel):
    query: str
    retmax: int = 10


class DatasetSearchResult(BaseModel):
    dataset: SRADataset
    evaluation: DatasetEvaluation


class DatasetSearchResponse(BaseModel):
    datasets: list[DatasetSearchResult]


@router.post(
    "/search",
    response_model=DatasetSearchResponse,
)
async def search_datasets(
    request: DatasetSearchRequest,
):
    query = request.query.strip()

    if not query:
        return DatasetSearchResponse(
            datasets=[],
        )

    discovered = study_dataset_discovery.discover(
        query,
        retmax=request.retmax,
    )

    results: list[DatasetSearchResult] = []

    for dataset, evaluation in discovered:
        results.append(
            DatasetSearchResult(
                dataset=dataset,
                evaluation=evaluation,
            )
        )

    return DatasetSearchResponse(
        datasets=results,
    )