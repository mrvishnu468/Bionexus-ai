
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.models.research_intent import (
    IntentField,
    IntentFieldStatus,
    IntentReviewStatus,
    ResearchIntent,
)
from app.services.intent_parser import ResearchIntentParser


class IntentProvider(Protocol):
    """Interface implemented by any AI provider adapter."""

    async def interpret(self, query: str) -> dict[str, Any]:
        """Return structured data matching the ResearchIntent schema."""
        ...


@dataclass
class InterpretationResult:
    intent: ResearchIntent
    source: Literal["ai", "rules_fallback"]
    warning: str | None = None


class ResearchIntentInterpreter:
    """Interpret research queries without bypassing researcher approval."""

    FIELD_NAMES = (
        "research_goal",
        "disease",
        "gene",
        "organism",
        "tissue",
        "assay_type",
        "analysis_goal",
        "comparison",
    )

    def __init__(
        self,
        provider: IntentProvider | None = None,
        fallback_parser: ResearchIntentParser | None = None,
    ) -> None:
        self.provider = provider
        self.fallback_parser = fallback_parser or ResearchIntentParser()

    
    @staticmethod
    def _enforce_proposed_status(
        intent: ResearchIntent,
        query: str,
        validate_explicit_evidence: bool = False,
    ) -> ResearchIntent:
        updates: dict[str, Any] = {
            "original_question": query,
            "review_status": IntentReviewStatus.PROPOSED,
        }
        normalized_query = query.casefold()

        for name in ResearchIntentInterpreter.FIELD_NAMES:
            field = getattr(intent, name)

            if not isinstance(field, IntentField):
                continue

            status = field.status

            if status == IntentFieldStatus.CONFIRMED:
                updates[name] = field.model_copy(
                    update={"status": IntentFieldStatus.INFERRED}
                )
            
            elif (
                validate_explicit_evidence
                and status == IntentFieldStatus.EXPLICIT
            ):
                has_grounded_evidence = any(
                    evidence.strip().casefold() in normalized_query
                    for evidence in field.evidence
                    if evidence.strip()
                )

                if not has_grounded_evidence:
                    updates[name] = field.model_copy(
                        update={"status": IntentFieldStatus.INFERRED}
                    )


        return intent.model_copy(update=updates)


    async def interpret(self, query: str) -> InterpretationResult:
        question = query.strip()
        if not question:
            raise ValueError("Research query cannot be empty.")

        if self.provider is not None:
            try:
                raw = await self.provider.interpret(question)
                intent = ResearchIntent.model_validate(raw)
                intent = self._enforce_proposed_status(intent, question, validate_explicit_evidence=True,)
                return InterpretationResult(
                    intent=intent,
                    source="ai",
                )
            except Exception:
                fallback_intent = self.fallback_parser.parse(question)
                fallback_intent = self._enforce_proposed_status(
                    fallback_intent,
                    question,
                )
                return InterpretationResult(
                    intent=fallback_intent,
                    source="rules_fallback",
                    warning=(
                        "AI interpretation was unavailable or invalid; "
                        "rule-based interpretation was used instead."
                    ),
                )

        fallback_intent = self.fallback_parser.parse(question)
        fallback_intent = self._enforce_proposed_status(
            fallback_intent,
            question,
        )
        return InterpretationResult(
            intent=fallback_intent,
            source="rules_fallback",
            warning="No AI provider is configured; rule-based interpretation was used.",
        )
