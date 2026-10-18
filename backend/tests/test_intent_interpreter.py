
import asyncio

import pytest

from app.models.research_intent import (
    IntentFieldStatus,
    IntentReviewStatus,
)
from app.services.intent_interpreter import ResearchIntentInterpreter
from app.services.intent_parser import ResearchIntentParser


class FakeAIProvider:
    def __init__(self, response):
        self.response = response

    async def interpret(self, query: str):
        return self.response


def test_ai_provider_output_is_validated_and_remains_proposed():
    proposed = ResearchIntentParser().parse(
        "breast cancer Homo sapiens RNA-Seq"
    )
    proposed.disease.evidence = ["breast cancer"]
    proposed.organism.evidence = ["Homo sapiens"]
    proposed.assay_type.evidence = ["RNA-Seq"]
    provider = FakeAIProvider(proposed.model_dump())
    interpreter = ResearchIntentInterpreter(provider=provider)

    result = asyncio.run(
        interpreter.interpret(
            "  breast cancer Homo sapiens RNA-Seq  "
        )
    )

    assert result.source == "ai"
    assert result.warning is None
    assert result.intent.original_question == (
        "breast cancer Homo sapiens RNA-Seq"
    )
    assert result.intent.review_status == IntentReviewStatus.PROPOSED


def test_invalid_ai_output_uses_disclosed_fallback():
    interpreter = ResearchIntentInterpreter(
        provider=FakeAIProvider({"unexpected": "invalid"})
    )

    result = asyncio.run(
        interpreter.interpret("breast cancer RNA-Seq")
    )

    assert result.source == "rules_fallback"
    assert result.warning is not None
    assert result.intent.review_status == IntentReviewStatus.PROPOSED


def test_no_provider_uses_rules_fallback():
    interpreter = ResearchIntentInterpreter()

    result = asyncio.run(
        interpreter.interpret("breast cancer RNA-Seq")
    )

    assert result.source == "rules_fallback"
    assert result.warning is not None
    assert result.intent.disease.value == "breast cancer"


def test_empty_query_is_rejected():
    interpreter = ResearchIntentInterpreter()

    with pytest.raises(ValueError):
        asyncio.run(interpreter.interpret("   "))


def test_ai_cannot_self_confirm_a_field():
    proposed = ResearchIntentParser().parse("breast cancer")
    proposed.disease.status = IntentFieldStatus.CONFIRMED
    interpreter = ResearchIntentInterpreter(
        provider=FakeAIProvider(proposed.model_dump())
    )

    result = asyncio.run(
        interpreter.interpret("breast cancer")
    )

    assert result.intent.review_status == IntentReviewStatus.PROPOSED
    assert result.intent.disease.status == IntentFieldStatus.INFERRED

def test_ungrounded_explicit_claim_is_downgraded():
    proposed = ResearchIntentParser().parse("find expression datasets")
    proposed.organism.value = "Homo sapiens"
    proposed.organism.status = IntentFieldStatus.EXPLICIT
    proposed.organism.evidence = ["Homo sapiens"]

    interpreter = ResearchIntentInterpreter(
        provider=FakeAIProvider(proposed.model_dump())
    )
    result = asyncio.run(
        interpreter.interpret("find expression datasets")
    )

    assert result.intent.organism.value == "Homo sapiens"
    assert result.intent.organism.status == IntentFieldStatus.INFERRED
    assert result.intent.review_status == IntentReviewStatus.PROPOSED
