from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.research_intent import (
    IntentReviewStatus,
    ResearchIntent,
)
from app.services.intent_approval import intent_approval_service
from app.services.intent_review import intent_review_service
from app.services.intent_service import intent_interpreter


router = APIRouter(prefix="/api/intent", tags=["Intent"])


class IntentInterpretationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)


class IntentInterpretationResponse(BaseModel):
    intent: ResearchIntent
    source: Literal["ai", "rules_fallback"]
    warning: str | None = None


class IntentApprovalRequest(BaseModel):
    intent: ResearchIntent


class IntentApprovalResponse(BaseModel):
    intent: ResearchIntent
    approval_token: str
    expires_in_seconds: int = 900


@router.post(
    "/interpret",
    response_model=IntentInterpretationResponse,
)
async def interpret_intent(
    request: IntentInterpretationRequest,
):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Research query cannot be empty.",
        )

    try:
        result = await intent_interpreter.interpret(query)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return IntentInterpretationResponse(
        intent=result.intent,
        source=result.source,
        warning=result.warning,
    )


@router.post(
    "/approve",
    response_model=IntentApprovalResponse,
)
async def approve_intent(
    request: IntentApprovalRequest,
):
    confirmed_intent = request.intent.model_copy(
        update={"review_status": IntentReviewStatus.CONFIRMED}
    )

    review = intent_review_service.review(confirmed_intent)

    if not review.ready_for_ranking:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Research criteria need clarification before approval."
                ),
                "clarification_questions": review.clarification_questions,
                "review_reasons": review.reasons,
            },
        )

    token = intent_approval_service.issue(confirmed_intent)

    return IntentApprovalResponse(
        intent=confirmed_intent,
        approval_token=token,
        expires_in_seconds=900,
    )