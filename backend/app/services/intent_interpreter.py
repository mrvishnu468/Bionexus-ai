
from dataclasses import dataclass
import re
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
        ...


@dataclass
class InterpretationResult:
    intent: ResearchIntent
    source: Literal["ai", "rules_fallback"]
    warning: str | None = None


class ResearchIntentInterpreter:
    """Interpret queries without bypassing researcher approval."""

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
        """Keep interpreted fields proposed and validate explicit evidence."""
        updates: dict[str, Any] = {
            "original_question": query,
            "review_status": IntentReviewStatus.PROPOSED,
        }
        normalized_query = query.casefold()

        for name in ResearchIntentInterpreter.FIELD_NAMES:
            field = getattr(intent, name)

            if not isinstance(field, IntentField):
                continue

            # AI output must never confirm a field automatically.
            if field.status == IntentFieldStatus.CONFIRMED:
                updates[name] = field.model_copy(
                    update={"status": IntentFieldStatus.INFERRED}
                )
                continue

            # Validate explicit evidence only for AI-provided results.
            if (
                not validate_explicit_evidence
                or field.status != IntentFieldStatus.EXPLICIT
            ):
                continue

            grounded = False

            for evidence in field.evidence:
                quoted = re.findall(
                    r"""['"]([^'"]+)['"]""",
                    evidence.strip(),
                )
                candidates = quoted or [evidence.strip()]

                if any(
                    phrase.casefold() in normalized_query
                    for phrase in candidates
                    if phrase
                ):
                    grounded = True
                    break

            if not grounded:
                updates[name] = field.model_copy(
                    update={"status": IntentFieldStatus.INFERRED}
                )

        return intent.model_copy(update=updates)

    @classmethod
    def _rules_are_sufficient(cls, intent: ResearchIntent) -> bool:
        """Skip AI when rules resolve a clear disease query."""
        if intent.disease.status != IntentFieldStatus.EXPLICIT:
            return False

        return not any(
            isinstance(getattr(intent, name), IntentField)
            and getattr(intent, name).status
            == IntentFieldStatus.AMBIGUOUS
            for name in cls.FIELD_NAMES
        )

    async def interpret(self, query: str) -> InterpretationResult:
        """Interpret a query while preserving researcher approval."""
        question = query.strip()

        if not question:
            raise ValueError("Research query cannot be empty.")

        rules_intent = self._enforce_proposed_status(
            self.fallback_parser.parse(question),
            question,
        )

        # Use deterministic rules when they resolve the query sufficiently.
        if self._rules_are_sufficient(rules_intent):
            return InterpretationResult(
                intent=rules_intent,
                source="rules_fallback",
            )

        # Use AI when rules cannot resolve the query sufficiently.
        if self.provider is not None:
            try:
                raw = await self.provider.interpret(question)
                intent = ResearchIntent.model_validate(raw)

                intent = self._enforce_proposed_status(
                    intent,
                    question,
                    validate_explicit_evidence=True,
                )

                return InterpretationResult(
                    intent=intent,
                    source="ai",
                )

            except Exception:
                fallback = self._enforce_proposed_status(
                    self.fallback_parser.parse(question),
                    question,
                )

                return InterpretationResult(
                    intent=fallback,
                    source="rules_fallback",
                    warning=(
                        "AI interpretation was unavailable or invalid; "
                        "rule-based interpretation was used instead."
                    ),
                )

        return InterpretationResult(
            intent=rules_intent,
            source="rules_fallback",
            warning=(
                "No AI provider is configured; rule-based "
                "interpretation was used."
            ),
        )
