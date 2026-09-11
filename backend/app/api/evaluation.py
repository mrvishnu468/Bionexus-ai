from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.dataset import SRADataset
from app.models.evaluation import DatasetEvaluation
from app.services.dataset_evaluator import dataset_evaluator
from app.tools.ncbi.entrez_client import ncbi_client


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Dataset Evaluation"],
)


class DatasetEvaluationRequest(BaseModel):
    accession: str


@router.post(
    "/dataset",
    response_model=DatasetEvaluation,
)
async def evaluate_dataset(
    request: DatasetEvaluationRequest,
):
    ids = ncbi_client.search_sra(
        request.accession,
        retmax=1,
    )

    if not ids:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    records = ncbi_client.fetch_sra_records(ids)
    datasets = ncbi_client.parse_sra_records(records)

    if not datasets:
        raise HTTPException(
            status_code=404,
            detail="Dataset metadata could not be parsed.",
        )

    dataset: SRADataset = datasets[0]

    return dataset_evaluator.evaluate(dataset)