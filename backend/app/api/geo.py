
from __future__ import annotations

import csv
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.analysis.geo_analysis_pipeline import (
    GeoAnalysisPipelineError,
    prepare_geo_analysis,
)
from app.analysis.geo_matrix_parser import parse_geo_expression_matrix
from app.analysis.matrix_validation import validate_geo_matrix
from app.analysis.r_runner import (
    RAnalysisError,
    run_limma,
    run_paired_limma,
)
from app.services.geo_cache import create_geo_expression_service
from app.services.geo_expression_service import (
    GeoExpressionService,
    GeoRetrievalError,
)
from app.services.geo_sample_verifier import verify_geo_pair
from app.tools.ncbi.geo_link_resolver import geo_link_resolver


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
    retrieved_at: str | None
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
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "cache",
        ),
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


@router.post("/prepare-analysis")
async def prepare_geo_series_analysis(
    request: GeoRetrievalRequest,
) -> dict:
    service = get_geo_service()

    try:
        return await prepare_geo_analysis(
            request.accession,
            geo_service=service,
        )
    except GeoAnalysisPipelineError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except GeoRetrievalError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GEO analysis preparation failed: {exc}",
        ) from exc


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


class GeoSRAResolutionRequest(BaseModel):
    study_accession: str = Field(
        ...,
        min_length=4,
        max_length=16,
        pattern=r"^SRP\d+$",
        description="SRA study accession, e.g. SRP123456",
    )


class GeoSRAResolutionResponse(BaseModel):
    study_accession: str
    status: str
    geo_accessions: list[str]
    mapping_confirmed: bool
    analysis_ready: bool
    message: str


@router.post(
    "/resolve-sra",
    response_model=GeoSRAResolutionResponse,
)
async def resolve_sra_to_geo(
    request: GeoSRAResolutionRequest,
) -> GeoSRAResolutionResponse:
    try:
        result = await run_in_threadpool(
            geo_link_resolver.resolve,
            request.study_accession,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"SRA-to-GEO resolution failed: {exc}",
        ) from exc

    if result.status == "resolved":
        status = "candidate"
        message = (
            "A possible GEO Series candidate was found. "
            "Explicit cross-reference verification is still required."
        )
    elif result.status == "ambiguous":
        status = "ambiguous"
        message = result.message
    else:
        status = "not_found"
        message = result.message

    return GeoSRAResolutionResponse(
        study_accession=result.study_accession,
        status=status,
        geo_accessions=list(result.geo_accessions),
        mapping_confirmed=False,
        analysis_ready=False,
        message=message,
    )


class GeoConfirmedSampleGroup(BaseModel):
    sample_accession: str = Field(..., min_length=1)
    group: str = Field(..., min_length=1)


class GeoApprovedPair(BaseModel):
    tumour_accession: str = Field(..., min_length=1)
    normal_accession: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    approved: bool


class GeoExecuteAnalysisRequest(GeoRetrievalRequest):
    assignments: list[GeoConfirmedSampleGroup] = Field(..., min_length=4)
    numerator_group: str = Field(..., min_length=1)
    denominator_group: str = Field(..., min_length=1)
    assay_type: str = Field(
        ...,
        pattern=r"^processed_microarray$",
        description=(
            "Only processed microarray data is supported by this endpoint."
        ),
    )
    normalization_confirmed: bool
    design_confirmed: bool
    paired_analysis: bool = False
    approved_pairs: list[GeoApprovedPair] = Field(default_factory=list)


@router.post("/execute-analysis")
async def execute_geo_analysis(
    request: GeoExecuteAnalysisRequest,
) -> dict:
    if not request.design_confirmed:
        raise HTTPException(
            status_code=422,
            detail="Researcher confirmation of the sample design is required.",
        )

    if not request.normalization_confirmed:
        raise HTTPException(
            status_code=422,
            detail="Confirm that the microarray expression values are normalized.",
        )

    numerator = request.numerator_group.strip()
    denominator = request.denominator_group.strip()

    if not numerator or not denominator or numerator == denominator:
        raise HTTPException(
            status_code=422,
            detail="Choose two distinct, non-empty comparison groups.",
        )

    if not request.paired_analysis and request.approved_pairs:
        raise HTTPException(
            status_code=422,
            detail=(
                "Approved patient pairs were supplied while paired analysis "
                "is disabled. Enable paired analysis or remove the pairs."
            ),
        )

    service = get_geo_service()

    try:
        matrix = await service.fetch(request.accession)
        validation = validate_geo_matrix(matrix)

        if validation["status"] == "blocked":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "The GEO matrix failed validation.",
                    "errors": validation.get("errors", []),
                },
            )

        representation = validation.get("data_representation")

        if representation not in {
            "nonnegative_continuous_values",
            "continuous_values_with_negatives",
        }:
            raise HTTPException(
                status_code=422,
                detail=(
                    "This endpoint accepts continuous processed microarray "
                    "values only. Integer-count RNA-seq data is not supported."
                ),
            )

        parsed = parse_geo_expression_matrix(matrix)
        expected_samples = list(parsed.sample_accessions)

        supplied_samples = [
            item.sample_accession.strip()
            for item in request.assignments
        ]

        if len(supplied_samples) != len(set(supplied_samples)):
            raise HTTPException(
                status_code=422,
                detail="Each sample must be assigned exactly once.",
            )

        if set(supplied_samples) != set(expected_samples):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Assignments must match the matrix sample accessions "
                    "exactly, with no missing or extra samples."
                ),
            )

        assignments = {
            item.sample_accession.strip(): item.group.strip()
            for item in request.assignments
        }

        if any(not group for group in assignments.values()):
            raise HTTPException(
                status_code=422,
                detail="Every sample must have a non-empty group assignment.",
            )

        groups = set(assignments.values())

        if numerator not in groups or denominator not in groups:
            raise HTTPException(
                status_code=422,
                detail="Both comparison groups must exist in the assignments.",
            )

        for group in (numerator, denominator):
            count = sum(value == group for value in assignments.values())
            if count < 2:
                raise HTTPException(
                    status_code=422,
                    detail=f"Group '{group}' requires at least two samples.",
                )

        approved_pair_records: list[dict[str, str | bool]] = []
        analysis_samples = expected_samples

        if request.paired_analysis:
            if not request.approved_pairs:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Paired analysis requires researcher-approved pairs."
                    ),
                )

            seen_samples: set[str] = set()
            seen_patients: set[str] = set()

            for pair in request.approved_pairs:
                tumour = pair.tumour_accession.strip()
                normal = pair.normal_accession.strip()
                patient = pair.patient_id.strip()

                if not pair.approved:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Pair {patient!r} has not been approved "
                            "by the researcher."
                        ),
                    )

                if not patient or not tumour or not normal:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Each pair requires a patient ID and both "
                            "sample accessions."
                        ),
                    )

                if tumour == normal:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Tumour and normal accessions must be different."
                        ),
                    )

                if patient in seen_patients:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Patient IDs must be unique across the submitted "
                            "complete pairs."
                        ),
                    )

                if tumour in seen_samples or normal in seen_samples:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "A sample cannot appear in more than one pair."
                        ),
                    )

                if tumour not in assignments or normal not in assignments:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Every paired sample must exist in the matrix "
                            "assignments."
                        ),
                    )

                if (
                    assignments[tumour] != numerator
                    or assignments[normal] != denominator
                ):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Tumour samples must match the numerator group "
                            "and normal samples the denominator group."
                        ),
                    )

                # Verify the sample records independently on the server.
                # Client-supplied approval alone is not sufficient.
                verification = await verify_geo_pair(tumour, normal)

                if verification.status != "corroborated":
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "message": (
                                f"Pair {patient!r} could not be corroborated "
                                "from GEO sample records."
                            ),
                            "tumour_accession": tumour,
                            "normal_accession": normal,
                            "verification_status": verification.status,
                            "evidence": verification.evidence,
                        },
                    )

                seen_patients.add(patient)
                seen_samples.update((tumour, normal))

                # This record is passed to run_paired_limma only after
                # the researcher approval and server verification succeed.
                approved_pair_records.append(
                    {
                        "tumour_accession": tumour,
                        "normal_accession": normal,
                        "patient_id": patient,
                        "approved": True,
                    }
                )

            if len(approved_pair_records) < 2:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Paired limma requires at least two complete "
                        "patient pairs."
                    ),
                )

            analysis_samples = [
                sample
                for pair in approved_pair_records
                for sample in (
                    str(pair["tumour_accession"]),
                    str(pair["normal_accession"]),
                )
            ]

        with tempfile.TemporaryDirectory(
            prefix="bionexus_geo_"
        ) as temp_dir:
            temp_path = Path(temp_dir)
            expression_path = temp_path / "expression.tsv"
            design_path = temp_path / "design.tsv"

            with expression_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.writer(handle, delimiter="\t")
                writer.writerow(["gene_id", *expected_samples])

                for feature_id, values in zip(
                    parsed.feature_ids,
                    parsed.values,
                    strict=True,
                ):
                    writer.writerow([feature_id, *values])

            with design_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.writer(handle, delimiter="\t")

                if request.paired_analysis:
                    writer.writerow(
                        ["sample_id", "group", "patient_id"]
                    )

                    patient_by_sample = {
                        str(pair["tumour_accession"]): str(pair["patient_id"])
                        for pair in approved_pair_records
                    }
                    patient_by_sample.update(
                        {
                            str(pair["normal_accession"]): str(pair["patient_id"])
                            for pair in approved_pair_records
                        }
                    )

                    for sample in analysis_samples:
                        writer.writerow(
                            [
                                sample,
                                assignments[sample],
                                patient_by_sample[sample],
                            ]
                        )
                else:
                    writer.writerow(["sample_id", "group"])

                    for sample in expected_samples:
                        writer.writerow([sample, assignments[sample]])

            if request.paired_analysis:
                results = await run_in_threadpool(
                    run_paired_limma,
                    str(expression_path),
                    str(design_path),
                    approved_pair_records,
                    numerator,
                    denominator,
                )
            else:
                results = await run_in_threadpool(
                    run_limma,
                    str(expression_path),
                    str(design_path),
                    numerator_group=numerator,
                    denominator_group=denominator,
                )

        return {
            "accession": matrix.accession,
            "title": matrix.title,
            "analysis_status": "completed",
            "analysis_method": (
                "paired_limma" if request.paired_analysis else "limma"
            ),
            "analysis_design": (
                "paired" if request.paired_analysis else "unpaired"
            ),
            "assay_type": request.assay_type,
            "comparison": {
                "numerator_group": numerator,
                "denominator_group": denominator,
                "direction": (
                    "Positive logFC indicates higher expression in "
                    f"{numerator}; negative logFC indicates higher "
                    f"expression in {denominator}."
                ),
            },
            "sample_count": len(analysis_samples),
            "patient_pair_count": (
                len(approved_pair_records)
                if request.paired_analysis
                else None
            ),
            "matrix_sha256": matrix.sha256,
            "source_url": matrix.source_url,
            "cache_hit": matrix.cache_hit,
            "retrieved_at": matrix.retrieved_at,
            "result_count": len(results),
            "results": results,
        }

    except HTTPException:
        raise
    except GeoRetrievalError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GEO retrieval failed: {exc}",
        ) from exc
    except RAnalysisError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Differential-expression analysis failed: {exc}",
        ) from exc
    except GeoAnalysisPipelineError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid analysis design: {exc}",
        ) from exc
