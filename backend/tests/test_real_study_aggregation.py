from app.services.study_aggregator import study_aggregator
from app.tools.ncbi.entrez_client import ncbi_client


def test_real_alzheimer_study_aggregation():
    ids = ncbi_client.search_sra(
        "SRP415133",
        retmax=10,
    )

    assert isinstance(ids, list)
    assert len(ids) > 0

    records = ncbi_client.fetch_sra_records(ids)
    datasets = ncbi_client.parse_sra_records(records)

    study_datasets = [
        dataset
        for dataset in datasets
        if dataset.study_accession == "SRP415133"
    ]

    assert len(study_datasets) > 0

    study = study_aggregator.aggregate(
        "SRP415133",
        study_datasets,
    )

    assert study.accession == "SRP415133"
    assert study.experiment_count > 0
    assert study.sample_count > 0
    assert study.run_count > 0
    assert study.organism == "Homo sapiens"