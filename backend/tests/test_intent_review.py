
from app.models.research_intent import (
    IntentField,
    IntentFieldStatus,
    IntentReviewStatus,
    ResearchIntent,
)
from app.services.intent_review import IntentReviewService


def test_clear_intent_can_proceed_to_ranking():
    intent = ResearchIntent(
        original_question="Find human bulk RNA-seq datasets",
        review_status=IntentReviewStatus.CONFIRMED,
        research_goal=IntentField(
            value="Dataset discovery",
            status=IntentFieldStatus.EXPLICIT,
        ),
        organism=IntentField(
            value="Homo sapiens",
            status=IntentFieldStatus.EXPLICIT,
        ),
        assay_type=IntentField(
            value="bulk_rna_seq",
            status=IntentFieldStatus.EXPLICIT,
        ),
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is True
    assert result.clarification_questions == []


def test_ambiguous_assay_requires_clarification():
    intent = ResearchIntent(
        original_question="Find expression datasets",
        assay_type=IntentField(
            value=None,
            status=IntentFieldStatus.AMBIGUOUS,
        ),
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is False
    assert any("assay type" in question for question in result.clarification_questions)


def test_existing_clarification_question_blocks_ranking():
    intent = ResearchIntent(
        original_question="Compare disease datasets",
        clarification_required=True,
        clarification_questions=[
            "Do you want disease versus control or early versus late disease?"
        ],
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is False
    assert len(result.clarification_questions) == 1



def test_missing_optional_tissue_does_not_block_ranking():
    intent = ResearchIntent(
        original_question="Find human RNA-seq datasets",
        review_status=IntentReviewStatus.CONFIRMED,
        research_goal=IntentField(
            value="Dataset discovery",
            status=IntentFieldStatus.EXPLICIT,
        ),
        organism=IntentField(
            value="Homo sapiens",
            status=IntentFieldStatus.EXPLICIT,
        ),

    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is True



def test_uninterpreted_intent_cannot_proceed_to_ranking():
    intent = ResearchIntent(
        original_question="Find expression datasets",
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is False
    assert result.clarification_questions
    assert result.reasons


def test_new_intent_starts_as_proposed():
    from app.models.research_intent import IntentReviewStatus

    intent = ResearchIntent(original_question="Find expression datasets")

    assert intent.review_status == IntentReviewStatus.PROPOSED


def test_researcher_confirmation_can_be_recorded():
    from app.models.research_intent import IntentReviewStatus

    intent = ResearchIntent(
        original_question="Find human RNA-seq datasets",
        review_status=IntentReviewStatus.CONFIRMED,
    )

    assert intent.review_status == IntentReviewStatus.CONFIRMED
def test_proposed_intent_requires_researcher_review():
    intent = ResearchIntent(
        original_question="Find human RNA-seq datasets",
        research_goal=IntentField(
            value="Dataset discovery",
            status=IntentFieldStatus.EXPLICIT,
        ),
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is False
    assert result.review_required is True
    assert result.clarification_questions == []
def test_confirmed_intent_with_ambiguity_stays_blocked():
    intent = ResearchIntent(
        original_question="Find expression datasets",
        review_status=IntentReviewStatus.CONFIRMED,
        research_goal=IntentField(
            value="Dataset discovery",
            status=IntentFieldStatus.EXPLICIT,
        ),
        assay_type=IntentField(
            value=None,
            status=IntentFieldStatus.AMBIGUOUS,
        ),
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is False
    assert result.clarification_questions


def test_confirmed_clear_intent_can_proceed():
    intent = ResearchIntent(
        original_question="Find human bulk RNA-seq datasets",
        review_status=IntentReviewStatus.CONFIRMED,
        research_goal=IntentField(
            value="Dataset discovery",
            status=IntentFieldStatus.EXPLICIT,
        ),
        organism=IntentField(
            value="Homo sapiens",
            status=IntentFieldStatus.EXPLICIT,
        ),
        assay_type=IntentField(
            value="bulk_rna_seq",
            status=IntentFieldStatus.EXPLICIT,
        ),
    )

    result = IntentReviewService().review(intent)

    assert result.ready_for_ranking is True
    assert result.review_required is False
    assert result.clarification_questions == []
