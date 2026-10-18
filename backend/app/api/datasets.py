
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.dataset import SRADataset
from app.models.evaluation import DatasetEvaluation
from app.models.research_intent import ResearchIntent
from app.services.intent_approval import (
    IntentApprovalError,
    intent_approval_service,
)
from app.services.intent_review import intent_review_service
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
    intent: ResearchIntent | None = None
    approval_token: str | None = None


class DatasetSearchResult(BaseModel):
    dataset: SRADataset
    evaluation: DatasetEvaluation


class DatasetSearchResponse(BaseModel):
    datasets: list[DatasetSearchResult] = Field(default_factory=list)
    review_required: bool = False
    ready_for_ranking: bool = True
    clarification_questions: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)


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

    intent = request.intent

    if intent is not None:
        if not request.approval_token:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Researcher approval is required before "
                    "dataset ranking."
                ),
            )

        try:
            intent_approval_service.verify(
                intent,
                request.approval_token,
            )
        except IntentApprovalError as exc:
            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc

        review = intent_review_service.review(intent)

        if not review.ready_for_ranking:
            return DatasetSearchResponse(
                datasets=[],
                review_required=review.review_required,
                ready_for_ranking=False,
                clarification_questions=review.clarification_questions,
                review_reasons=review.reasons,
            )

    discovered = study_dataset_discovery.discover(
        query,
        retmax=request.retmax,
        intent=intent,
    )

    results = [
        DatasetSearchResult(
            dataset=dataset,
            evaluation=evaluation,
        )
        for dataset, evaluation in discovered
    ]

    return DatasetSearchResponse(
        datasets=results,
        review_required=False,
        ready_for_ranking=True,
    )
