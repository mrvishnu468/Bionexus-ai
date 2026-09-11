from fastapi import APIRouter
from pydantic import BaseModel

from app.models.dataset import SRADataset
from app.tools.ncbi.entrez_client import ncbi_client


router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


class DatasetSearchRequest(BaseModel):
    query: str
    retmax: int = 10


class DatasetSearchResponse(BaseModel):
    datasets: list[SRADataset]


@router.post("/search", response_model=DatasetSearchResponse)
async def search_datasets(request: DatasetSearchRequest):
    ids = ncbi_client.search_sra(
        request.query,
        retmax=request.retmax,
    )

    records = ncbi_client.fetch_sra_records(ids)

    datasets = ncbi_client.parse_sra_records(records)

    return DatasetSearchResponse(
        datasets=datasets,
    )