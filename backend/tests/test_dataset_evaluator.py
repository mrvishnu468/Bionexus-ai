
from app.models.dataset import SRADataset
from app.models.evaluation import DatasetSuitability
from app.models.research_intent import (
    IntentField,
    IntentFieldStatus,
    IntentReviewStatus,
    ResearchIntent,
)
from app.services.dataset_evaluator import dataset_evaluator


def test_bulk_human_dataset_is_recommended():
    dataset = SRADataset(
        accession="TEST_BULK_001",
        study_accession="TEST_STUDY_001",
        title="Human bulk RNA-seq study",
        organism="Homo sapiens",
        library_strategy="RNA-Seq",
        library_source="TRANSCRIPTOMIC",
        description="Bulk transcriptomic sequencing.",
        sample_count=6,
        run_count=6,
        study_title="Human transcriptomic study",
        study_abstract="A human bulk RNA-seq experiment.",
        experiment_type="TRANSCRIPTOMIC",
    )

    evaluation = dataset_evaluator.evaluate(dataset)

    assert evaluation.suitability == DatasetSuitability.RECOMMENDED
    assert evaluation.score >= 80
    assert len(evaluation.reasons) > 0


def test_single_nucleus_dataset_is_conditional():
    dataset = SRADataset(
        accession="SRX18881957",
        study_accession="SRP415133",
        title="Donor22,V1",
        organism="Homo sapiens",
        library_strategy="RNA-Seq",
        library_source="TRANSCRIPTOMIC SINGLE CELL",
        description="Single-nucleus cDNA libraries.",
        sample_count=1,
        run_count=1,
        study_title="Transcriptomic changes in Alzheimer disease",
        study_abstract="Single-nucleus RNA sequencing study.",
        experiment_type="TRANSCRIPTOMIC SINGLE CELL",
    )

    evaluation = dataset_evaluator.evaluate(dataset)

    assert evaluation.suitability == DatasetSuitability.CONDITIONAL
    assert any(
        "specialized analysis" in warning
        for warning in evaluation.warnings
    )


def test_single_cell_dataset_remains_conditional_with_many_samples():
    dataset = SRADataset(
        accession="TEST_SINGLE_CELL_001",
        study_accession="TEST_STUDY_002",
        title="Human single-cell RNA-seq study",
        organism="Homo sapiens",
        library_strategy="RNA-Seq",
        library_source="TRANSCRIPTOMIC SINGLE CELL",
        description="Single-cell transcriptomic sequencing.",
        sample_count=50,
        run_count=50,
        study_title="Human single-cell study",
        study_abstract="A human single-cell RNA-seq experiment.",
        experiment_type="TRANSCRIPTOMIC SINGLE CELL",
    )

    evaluation = dataset_evaluator.evaluate(dataset)

    assert evaluation.suitability == DatasetSuitability.CONDITIONAL
    assert any(
        "specialized analysis" in warning
        for warning in evaluation.warnings
    )


def test_single_nucleus_dataset_is_conditional():
    dataset = SRADataset(
        accession="TEST_SINGLE_NUCLEUS_001",
        study_accession="TEST_STUDY_003",
        title="Human single-nucleus RNA-seq study",
        organism="Homo sapiens",
        library_strategy="RNA-Seq",
        library_source="TRANSCRIPTOMIC SINGLE NUCLEUS",
        description="Single-nucleus transcriptomic sequencing.",
        sample_count=20,
        run_count=20,
        study_title="Human single-nucleus study",
        study_abstract="A human single-nucleus RNA-seq experiment.",
        experiment_type="TRANSCRIPTOMIC SINGLE NUCLEUS",
    )

    evaluation = dataset_evaluator.evaluate(dataset)

    assert evaluation.suitability == DatasetSuitability.CONDITIONAL
    assert any(
        "specialized analysis" in warning
        for warning in evaluation.warnings
    )


def test_non_transcriptomic_source_is_not_marked_as_transcriptomic():
    dataset = SRADataset(
        accession="TEST_NON_TRANSCRIPTOMIC_001",
        study_accession="TEST_STUDY_004",
        title="Human sequencing study",
        organism="Homo sapiens",
        library_strategy="RNA-Seq",
        library_source="GENOMIC",
        description="Genomic sequencing.",
        sample_count=6,
        run_count=6,
        study_title="Human genomic study",
        study_abstract="A human genomic sequencing experiment.",
        experiment_type="GENOMIC",
    )

    evaluation = dataset_evaluator.evaluate(dataset)

    assert any(
        "Transcriptomic library source could not be confirmed." in warning
        for warning in evaluation.warnings
    )


def test_non_human_organism_is_not_penalized_without_preference():
    dataset = SRADataset(
        accession="TEST_MOUSE_001",
        study_accession="TEST_STUDY_MOUSE",
        title="Mouse bulk RNA-seq study",
        organism="Mus musculus",
        library_strategy="RNA-Seq",
        library_source="TRANSCRIPTOMIC",
        description="Bulk transcriptomic sequencing.",
        sample_count=6,
        run_count=6,
        study_title="Mouse transcriptomic study",
        study_abstract="A mouse bulk RNA-seq experiment.",
        experiment_type="TRANSCRIPTOMIC",
    )

    evaluation = dataset_evaluator.evaluate(dataset)

    assert evaluation.relevance_score == 50
    assert evaluation.readiness_score == 100


def test_low_relevance_does_not_automatically_mean_recommended():
    dataset = SRADataset(
        accession="TEST_UNRELATED_001",
        study_accession="TEST_STUDY_UNRELATED",
        title="Mouse bulk RNA-seq study",
        organism="Mus musculus",
        library_strategy="RNA-Seq",
        library_source="TRANSCRIPTOMIC",
        description="Bulk transcriptomic sequencing.",
        sample_count=6,
        run_count=6,
        study_title="Mouse transcriptomic study",
        study_abstract="A mouse bulk RNA-seq experiment.",
        experiment_type="TRANSCRIPTOMIC",
    )

    intent = ResearchIntent(
        original_question="Find human breast cancer datasets",
        review_status=IntentReviewStatus.CONFIRMED,
        research_goal=IntentField(
            value="differential expression",
            status=IntentFieldStatus.CONFIRMED,
        ),
        organism=IntentField(
            value="Homo sapiens",
            status=IntentFieldStatus.CONFIRMED,
        ),
        disease=IntentField(
            value="breast cancer",
            status=IntentFieldStatus.EXPLICIT,
        ),
    )

    evaluation = dataset_evaluator.evaluate(dataset, intent=intent)

    assert evaluation.relevance_score == 0
    assert evaluation.suitability != DatasetSuitability.RECOMMENDED
