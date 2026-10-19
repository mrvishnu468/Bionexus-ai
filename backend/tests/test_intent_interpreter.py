
import asyncio

import pytest

from app.models.research_intent import (
    IntentFieldStatus,
    IntentReviewStatus,
)
from app.services.intent_interpreter import ResearchIntentInterpreter
from app.services.intent_parser import ResearchIntentParser


UNKNOWN_QUERY = "unknown condition"


class FakeAIProvider:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    async def interpret(self, query: str):
        self.calls += 1
        return self.response


def ai_intent(query="unknown condition Homo sapiens RNA-Seq"):
    proposed = ResearchIntentParser().parse(query)

    proposed.disease.value = "unknown condition"
    proposed.disease.status = IntentFieldStatus.EXPLICIT
    proposed.disease.evidence = ["unknown condition"]

    proposed.organism.value = "Homo sapiens"
    proposed.organism.status = IntentFieldStatus.EXPLICIT
    proposed.organism.evidence = ["Homo sapiens"]

    proposed.assay_type.value = "RNA-Seq"
    proposed.assay_type.status = IntentFieldStatus.EXPLICIT
    proposed.assay_type.evidence = ["RNA-Seq"]

    return proposed


def test_ai_output_is_validated_and_remains_proposed():
    query = "unknown condition Homo sapiens RNA-Seq"
    proposed = ai_intent(query)
    provider = FakeAIProvider(proposed.model_dump())
    interpreter = ResearchIntentInterpreter(provider=provider)

    result = asyncio.run(interpreter.interpret(f"  {query}  "))

    assert result.source == "ai"
    assert result.warning is None
    assert result.intent.original_question == query
    assert result.intent.review_status == IntentReviewStatus.PROPOSED
    assert provider.calls == 1


def test_invalid_ai_output_uses_disclosed_fallback():
    interpreter = ResearchIntentInterpreter(
        provider=FakeAIProvider({"unexpected": "invalid"})
    )

    result = asyncio.run(
        interpreter.interpret("unknown condition RNA-Seq")
    )

    assert result.source == "rules_fallback"
    assert result.warning is not None
    assert result.intent.review_status == IntentReviewStatus.PROPOSED


def test_no_provider_uses_rules_fallback():
    result = asyncio.run(
        ResearchIntentInterpreter().interpret("breast cancer RNA-Seq")
    )

    assert result.source == "rules_fallback"
    assert result.warning is None
    assert result.intent.disease.value == "breast cancer"


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        asyncio.run(ResearchIntentInterpreter().interpret("   "))


def test_ai_cannot_self_confirm_a_field():
    query = "unknown condition"
    proposed = ai_intent(query)
    proposed.disease.status = IntentFieldStatus.CONFIRMED

    provider = FakeAIProvider(proposed.model_dump())
    interpreter = ResearchIntentInterpreter(provider=provider)

    result = asyncio.run(interpreter.interpret(query))

    assert result.source == "ai"
    assert result.intent.review_status == IntentReviewStatus.PROPOSED
    assert result.intent.disease.status == IntentFieldStatus.INFERRED
    assert provider.calls == 1


def test_ungrounded_explicit_claim_is_downgraded():
    proposed = ResearchIntentParser().parse("find expression datasets")
    proposed.organism.value = "Homo sapiens"
    proposed.organism.status = IntentFieldStatus.EXPLICIT
    proposed.organism.evidence = ["Homo sapiens"]

    provider = FakeAIProvider(proposed.model_dump())
    interpreter = ResearchIntentInterpreter(provider=provider)

    result = asyncio.run(
        interpreter.interpret("find expression datasets")
    )

    assert result.intent.organism.value == "Homo sapiens"
    assert result.intent.organism.status == IntentFieldStatus.INFERRED
    assert result.intent.review_status == IntentReviewStatus.PROPOSED
    assert provider.calls == 1


def test_confident_rules_skip_ai_provider():
    provider = FakeAIProvider({})
    interpreter = ResearchIntentInterpreter(provider=provider)

    result = asyncio.run(
        interpreter.interpret("breast cancer RNA-Seq")
    )

    assert result.source == "rules_fallback"
    assert result.warning is None
    assert result.intent.disease.value == "breast cancer"
    assert result.intent.review_status == IntentReviewStatus.PROPOSED
    assert provider.calls == 0


def test_unknown_disease_uses_ai_provider():
    proposed = ai_intent()
    provider = FakeAIProvider(proposed.model_dump())
    interpreter = ResearchIntentInterpreter(provider=provider)

    result = asyncio.run(
        interpreter.interpret("unknown condition RNA-Seq")
    )

    assert result.source == "ai"
    assert provider.calls == 1
