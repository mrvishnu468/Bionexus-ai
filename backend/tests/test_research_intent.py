
from app.models.research_intent import (
    IntentField,
    IntentFieldStatus,
    ResearchIntent,
)


def test_research_intent_preserves_original_question():
    question = "Find human RNA-seq datasets for Alzheimer disease"

    intent = ResearchIntent(original_question=question)

    assert intent.original_question == question


def test_research_intent_fields_default_to_unknown():
    intent = ResearchIntent(original_question="Study gene expression")

    fields = [
        intent.research_goal,
        intent.disease,
        intent.gene,
        intent.organism,
        intent.tissue,
        intent.assay_type,
        intent.analysis_goal,
        intent.comparison,
    ]

    assert all(field.status == IntentFieldStatus.UNKNOWN for field in fields)
    assert all(field.value is None for field in fields)


def test_intent_field_preserves_evidence_and_status():
    field = IntentField(
        value="Homo sapiens",
        status=IntentFieldStatus.EXPLICIT,
        evidence=["The researcher specified human samples."],
    )

    assert field.value == "Homo sapiens"
    assert field.status == IntentFieldStatus.EXPLICIT
    assert len(field.evidence) == 1


def test_clarification_state_defaults_to_not_required():
    intent = ResearchIntent(original_question="Study gene expression")

    assert intent.clarification_required is False
    assert intent.clarification_questions == []


def test_intent_defaults_are_independent():
    first = ResearchIntent(original_question="First question")
    second = ResearchIntent(original_question="Second question")

    first.constraints.append("Human samples only")
    first.disease.evidence.append("Explicitly mentioned")

    assert second.constraints == []
    assert second.disease.evidence == []
