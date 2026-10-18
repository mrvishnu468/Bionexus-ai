
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.analysis.matrix_validation import validate_geo_matrix
from app.services.geo_cache import create_geo_expression_service
from app.services.geo_expression_service import (
    GeoRetrievalError,
    GeoExpressionService,
)

router = APIRouter(prefix="/api/geo", tags=["GEO expression data"])


class GeoRetrievalRequest(BaseModel):
    accession: str = Field(
        ...,
        min_length=4,
        max_length=16,
        pattern=r"^GSE\d+$",
        description="NCBI GEO Series accession, e.g. GSE10072",
    )


class GeoRetrievalResponse(BaseModel):
    accession: str
    title: str
    source_url: str
    sample_accessions: list[str]
    matrix_rows: int
    matrix_columns: int
    compressed_bytes: int
    sha256: str
    accessed_at: str
    retrieved_at: str
    cache_hit: bool
class GeoMatrixValidationResponse(BaseModel):
    accession: str
    title: str
    status: str
    ready_for_design_review: bool
    assay_type: str
    data_representation: str
    platform_ids: list[str]
    matrix_rows: int
    matrix_columns: int
    metadata_sample_count: int
    sample_ids_aligned: bool
    duplicate_feature_ids: int
    ragged_rows: int
    missing_values: int
    invalid_numeric_values: int
    non_finite_values: int
    observed_values: int
    minimum_value: float | None
    maximum_value: float | None
    negative_values: int
    non_integer_values: int
    inferred_sample_groups: dict[str, int]
    sample_group_evidence: dict[str, int]
    errors: list[str]
    warnings: list[str]

@lru_cache(maxsize=1)
def get_geo_service() -> GeoExpressionService:
    cache_root = os.getenv(
        "BIONEXUS_CACHE_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "cache"),
    )
    return create_geo_expression_service(cache_root)


@router.post("/retrieve", response_model=GeoRetrievalResponse)
async def retrieve_geo_series(
    request: GeoRetrievalRequest,
) -> GeoRetrievalResponse:
    service = get_geo_service()

    try:
        result = await service.fetch(request.accession)
    except GeoRetrievalError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GEO retrieval failed: {exc}",
        ) from exc

    return GeoRetrievalResponse(
        accession=result.accession,
        title=result.title,
        source_url=result.source_url,
        sample_accessions=result.sample_accessions,
        matrix_rows=result.matrix_rows,
        matrix_columns=result.matrix_columns,
        compressed_bytes=result.compressed_bytes,
        sha256=result.sha256,
        accessed_at=result.accessed_at,
        retrieved_at=result.retrieved_at,
        cache_hit=result.cache_hit,
    )
@router.post(
    "/validate",
    response_model=GeoMatrixValidationResponse,
)
async def validate_geo_series(
    request: GeoRetrievalRequest,
) -> GeoMatrixValidationResponse:
    service = get_geo_service()

    try:
        matrix = await service.fetch(request.accession)
        report = validate_geo_matrix(matrix)
    except GeoRetrievalError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GEO matrix validation failed: {exc}",
        ) from exc

    return GeoMatrixValidationResponse(**report)