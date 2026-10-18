from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.experimental_design import (
    ExperimentalDesign,
    ExperimentalGroup,
)
from app.models.sample_groups import GroupDetectionResult
from app.services.experimental_design_evaluator import (
    experimental_design_evaluator,
)
from app.services.study_group_analyzer import study_group_analyzer


router = APIRouter(
    prefix="/api/study-design",
    tags=["Study Design"],
)


class StudyDesignReviewRequest(BaseModel):
    study_accession: str
    retmax: int = Field(default=100, ge=1, le=500)
    metadata_complete_confirmed: bool = False
    biological_replicates_confirmed: bool = False


class StudyDesignReviewResponse(BaseModel):
    study_accession: str
    group_detection: GroupDetectionResult
    design_suitable: bool
    design_reasons: list[str] = Field(default_factory=list)


@router.post(
    "/review",
    response_model=StudyDesignReviewResponse,
)
async def review_study_design(
    request: StudyDesignReviewRequest,
):
    study_accession = request.study_accession.strip()

    if not study_accession:
        raise HTTPException(
            status_code=422,
            detail="A study accession is required.",
        )

    detection = study_group_analyzer.analyze(
        study_accession,
        retmax=request.retmax,
    )

    if not detection.groups:
        return StudyDesignReviewResponse(
            study_accession=study_accession,
            group_detection=detection,
            design_suitable=False,
            design_reasons=[
                "Experimental groups could not be established "
                "from the available sample metadata."
            ],
        )

    control_names = {
        "control",
        "healthy",
        "healthy control",
        "normal",
        "normal control",
        "unaffected",
        "wild type",
        "wild-type",
        "wt",
    }

    has_control_group = any(
        group.name.strip().lower() in control_names
        for group in detection.groups
    )

    design = ExperimentalDesign(
        groups=[
            ExperimentalGroup(
                name=group.name,
                sample_count=len(group.sample_accessions),
            )
            for group in detection.groups
        ],
        has_biological_replicates=(
            request.biological_replicates_confirmed
        ),
        has_control_group=has_control_group,
        metadata_complete=request.metadata_complete_confirmed,
        notes=detection.warnings,
    )

    suitable, reasons = experimental_design_evaluator.evaluate(
        design
    )

    return StudyDesignReviewResponse(
        study_accession=study_accession,
        group_detection=detection,
        design_suitable=suitable,
        design_reasons=reasons,
    )