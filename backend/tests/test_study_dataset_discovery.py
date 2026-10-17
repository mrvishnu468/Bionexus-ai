from app.models.dataset import SRADataset
from app.models.evaluation import DatasetAssayType
from app.services.dataset_evaluator import DatasetEvaluator


def make_dataset(
    source: str,
    experiment_type: str = "",
    description: str = "",
    title: str = "",
    study_title: str = "",
    study_abstract: str = "",
) -> SRADataset:
    return SRADataset(
        accession="SRXTEST",
        study_accession="SRPTEST",
        organism="Homo sapiens",
        library_strategy="RNA-Seq",
        library_source=source,
        experiment_type=experiment_type,
        description=description,
        title=title,
        study_title=study_title,
        study_abstract=study_abstract,
        sample_count=10,
        run_count=10,
        samples=[],
    )


def test_single_nucleus_classification():
    evaluator = DatasetEvaluator()

    dataset = make_dataset(
        source="TRANSCRIPTOMIC SINGLE CELL",
        description="Single-nucleus RNA sequencing study.",
    )

    result = evaluator._classify_assay(dataset)

    assert result == DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ


def test_single_cell_classification():
    evaluator = DatasetEvaluator()

    dataset = make_dataset(
        source="TRANSCRIPTOMIC",
        description="Single-cell RNA sequencing study.",
    )

    result = evaluator._classify_assay(dataset)

    assert result == DatasetAssayType.SINGLE_CELL_RNA_SEQ


def test_bulk_rna_seq_classification():
    evaluator = DatasetEvaluator()

    dataset = make_dataset(
        source="TRANSCRIPTOMIC",
        description="Bulk RNA sequencing study.",
    )

    result = evaluator._classify_assay(dataset)

    assert result == DatasetAssayType.BULK_RNA_SEQ


def test_single_nucleus_detected_from_study_abstract():
    evaluator = DatasetEvaluator()

    dataset = make_dataset(
        source="TRANSCRIPTOMIC",
        study_abstract=(
            "We performed single-nucleus RNA-sequencing "
            "on human brain samples."
        ),
    )

    result = evaluator._classify_assay(dataset)

    assert result == DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ
from app.services.study_dataset_discovery import StudyDatasetDiscovery


def test_study_aggregation(monkeypatch):
    discovery = StudyDatasetDiscovery()

    datasets = [
        SRADataset(
            accession="SRX001",
            study_accession="SRP001",
            organism="Homo sapiens",
            library_strategy="RNA-Seq",
            library_source="TRANSCRIPTOMIC",
            study_title="Test study",
            study_abstract="Test abstract",
            sample_count=2,
            run_count=2,
            samples=[
                {"accession": "SRS001"},
                {"accession": "SRS002"},
            ],
        ),
        SRADataset(
            accession="SRX002",
            study_accession="SRP001",
            organism="Homo sapiens",
            library_strategy="RNA-Seq",
            library_source="TRANSCRIPTOMIC",
            study_title="Test study",
            study_abstract="Test abstract",
            sample_count=3,
            run_count=3,
            samples=[
                {"accession": "SRS003"},
                {"accession": "SRS004"},
                {"accession": "SRS005"},
            ],
        ),
    ]

    monkeypatch.setattr(
        discovery,
        "_collect_study",
        lambda study_accession: SRADataset(
            accession="SRX001",
            study_accession=study_accession,
            organism="Homo sapiens",
            library_strategy="RNA-Seq",
            library_source="TRANSCRIPTOMIC",
            study_title="Test study",
            study_abstract="Test abstract",
            sample_count=5,
            run_count=5,
            samples=[
                {"accession": "SRS001"},
                {"accession": "SRS002"},
                {"accession": "SRS003"},
                {"accession": "SRS004"},
                {"accession": "SRS005"},
            ],
        ),
    )

    monkeypatch.setattr(
        discovery,
        "_StudyDatasetDiscovery__unused",
        None,
        raising=False,
    )

    monkeypatch.setattr(
        "app.services.study_dataset_discovery.ncbi_client.search_sra",
        lambda query, retmax: ["1", "2"],
    )

    monkeypatch.setattr(
        "app.services.study_dataset_discovery.ncbi_client.fetch_sra_records",
        lambda ids: "<mocked/>",
    )

    monkeypatch.setattr(
        "app.services.study_dataset_discovery.ncbi_client.parse_sra_records",
        lambda records: datasets,
    )

    results = discovery.discover(
        "test query",
        retmax=2,
    )

    assert len(results) == 1

    study, evaluation = results[0]

    assert study.study_accession == "SRP001"
    assert study.sample_count == 5
    assert study.run_count == 5
    assert len(study.samples) == 5
    assert evaluation.score == round(0.60 * evaluation.relevance_score+ 0.40 * evaluation.readiness_score)