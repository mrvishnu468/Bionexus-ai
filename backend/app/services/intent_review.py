
from pydantic import BaseModel, Field

from app.models.research_intent import (
    IntentFieldStatus,
    IntentReviewStatus,
    ResearchIntent,
)


class IntentReviewResult(BaseModel):
    ready_for_ranking: bool
    review_required: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class IntentReviewService:
    MATERIAL_FIELDS = (
        "research_goal",
        "disease",
        "gene",
        "organism",
        "assay_type",
        "analysis_goal",
        "comparison",
    )

    def review(self, intent: ResearchIntent) -> IntentReviewResult:
        questions = list(intent.clarification_questions)
        reasons: list[str] = []

        interpreted_goal = (
            intent.research_goal.status
            in {
                IntentFieldStatus.EXPLICIT,
                IntentFieldStatus.INFERRED,
                IntentFieldStatus.CONFIRMED,
            }
            and bool(intent.research_goal.value)
        )

        if not interpreted_goal:
            reasons.append(
                "The research goal has not been established."
            )
            if not questions:
                questions.append(
                    "What research goal are you trying to achieve?"
                )

        for field_name in self.MATERIAL_FIELDS:
            field = getattr(intent, field_name)

            if field.status == IntentFieldStatus.AMBIGUOUS:
                reasons.append(
                    f"The '{field_name}' field has multiple possible interpretations."
                )
                question = (
                    f"Please clarify the intended "
                    f"{field_name.replace('_', ' ')}."
                )
                if question not in questions:
                    questions.append(question)

        if intent.clarification_required and not questions:
            questions.append(
                "Please clarify the research requirements before final ranking."
            )



        review_required = (
            intent.review_status == IntentReviewStatus.PROPOSED
        )

        ready = (
            interpreted_goal
            and intent.review_status == IntentReviewStatus.CONFIRMED
            and not questions
            and not intent.clarification_required
        )

        if ready:
            reasons.append(
                "The research goal is established and no unresolved "
                "clarification requirement was found."
            )

        return IntentReviewResult(
            ready_for_ranking=ready,
            review_required=review_required,
            clarification_questions=questions,
            reasons=reasons,
        )


intent_review_service = IntentReviewService()
