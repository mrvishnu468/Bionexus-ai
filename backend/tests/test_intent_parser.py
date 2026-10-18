import json

from app.models.research_intent import ResearchIntent
from app.models.research_intent import (
    IntentFieldStatus,
    IntentReviewStatus,
)
from app.services.intent_parser import ResearchIntentParser


def test_parses_breast_cancer_human_rna_seq_query():
    intent = ResearchIntentParser().parse(
        "breast cancer Homo sapiens RNA-Seq"
    )

    assert intent.disease.value == "breast cancer"
    assert intent.organism.value == "Homo sapiens"
    assert intent.assay_type.value == "RNA-Seq"
    assert intent.tissue.status == IntentFieldStatus.UNKNOWN
    assert intent.review_status == IntentReviewStatus.PROPOSED


def test_human_alias_is_normalized():
    intent = ResearchIntentParser().parse(
        "Find human RNA sequencing datasets"
    )

    assert intent.organism.value == "Homo sapiens"
    assert intent.assay_type.value == "RNA-Seq"


def test_missing_criteria_remain_unknown():
    intent = ResearchIntentParser().parse(
        "Find gene expression datasets"
    )

    assert intent.disease.status == IntentFieldStatus.UNKNOWN
    assert intent.organism.status == IntentFieldStatus.UNKNOWN
    assert intent.tissue.status == IntentFieldStatus.UNKNOWN
    assert intent.assay_type.status == IntentFieldStatus.UNKNOWN


def test_multiple_organisms_require_clarification():
    intent = ResearchIntentParser().parse(
        "Compare human and mouse RNA-Seq datasets"
    )

    assert intent.organism.status == IntentFieldStatus.AMBIGUOUS


def test_parser_never_confirms_intent_automatically():
    intent = ResearchIntentParser().parse(
        "breast cancer Homo sapiens RNA-Seq"
    )

    assert intent.review_status == IntentReviewStatus.PROPOSED
    assert intent.research_goal.status == IntentFieldStatus.INFERRED
def test_intent_serializes_to_json_without_losing_review_state():
    intent = ResearchIntentParser().parse(
        "breast cancer Homo sapiens RNA-Seq"
    )

    payload = json.loads(intent.model_dump_json())
    restored = ResearchIntent.model_validate(payload)

    assert restored.original_question == intent.original_question
    assert restored.disease.value == "breast cancer"
    assert restored.disease.status == IntentFieldStatus.EXPLICIT
    assert restored.organism.value == "Homo sapiens"
    assert restored.review_status == IntentReviewStatus.PROPOSED
    assert restored.disease.evidence == intent.disease.evidence
    
def test_extracts_explicit_tumor_vs_healthy_comparison():
    intent = ResearchIntentParser().parse(
        "Find public RNA-seq datasets for breast cancer in "
        "Homo sapiens comparing tumor tissue with healthy controls."
    )

    assert intent.comparison.value == (
        "tumor tissue vs healthy controls"
    )
    assert intent.comparison.status == IntentFieldStatus.EXPLICIT
    assert intent.comparison.evidence


def test_comparison_remains_unknown_when_not_stated():
    intent = ResearchIntentParser().parse(
        "Find RNA-seq datasets for breast cancer in Homo sapiens."
    )

    assert intent.comparison.value is None
    assert intent.comparison.status == IntentFieldStatus.UNKNOWN


def test_extracts_comparison_using_versus():
    intent = ResearchIntentParser().parse(
        "Compare tumor samples versus healthy controls "
        "for breast cancer RNA-seq."
    )

    assert intent.comparison.value == (
        "tumor samples vs healthy controls"
    )
    assert intent.comparison.status == IntentFieldStatus.EXPLICIT