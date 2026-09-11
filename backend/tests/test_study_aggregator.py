from app.models.dataset import SRADataset
from app.services.study_aggregator import study_aggregator


def test_study_aggregation():
    datasets = [
        SRADataset(
            accession="SRX_TEST_001",
            study_accession="SRP_TEST_001",
            organism="Homo sapiens",
            library_strategy="RNA-Seq",
            library_source="TRANSCRIPTOMIC",
            study_title="Test RNA-seq study",
            study_abstract="Test study abstract.",
            sample_count=1,
            run_count=2,
        ),
        SRADataset(
            accession="SRX_TEST_002",
            study_accession="SRP_TEST_001",
            organism="Homo sapiens",
            library_strategy="RNA-Seq",
            library_source="TRANSCRIPTOMIC",
            study_title="Test RNA-seq study",
            study_abstract="Test study abstract.",
            sample_count=1,
            run_count=2,
        ),
        SRADataset(
            accession="SRX_TEST_003",
            study_accession="SRP_TEST_001",
            organism="Homo sapiens",
            library_strategy="RNA-Seq",
            library_source="TRANSCRIPTOMIC",
            study_title="Test RNA-seq study",
            study_abstract="Test study abstract.",
            sample_count=1,
            run_count=2,
        ),
    ]

    study = study_aggregator.aggregate(
        "SRP_TEST_001",
        datasets,
    )

    assert study.accession == "SRP_TEST_001"
    assert study.experiment_count == 3
    assert study.sample_count == 3
    assert study.run_count == 6
    assert study.organism == "Homo sapiens"
    assert len(study.experiments) == 3


def test_empty_study_aggregation():
    study = study_aggregator.aggregate(
        "SRP_EMPTY",
        [],
    )

    assert study.accession == "SRP_EMPTY"
    assert study.experiment_count == 0
    assert study.sample_count == 0
    assert study.run_count == 0
    assert study.experiments == []