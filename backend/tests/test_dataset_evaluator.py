from app.models.dataset import SRADataset
from app.models.evaluation import DatasetSuitability
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