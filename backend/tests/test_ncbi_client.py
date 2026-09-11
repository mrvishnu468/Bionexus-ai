from app.tools.ncbi.entrez_client import ncbi_client


def test_search_sra():
    ids = ncbi_client.search_sra(
        "Alzheimer disease AND Homo sapiens AND RNA-Seq",
        retmax=5,
    )

    assert isinstance(ids, list)
    assert len(ids) <= 5


def test_fetch_sra_records():
    ids = ncbi_client.search_sra(
        "Alzheimer disease AND Homo sapiens AND RNA-Seq",
        retmax=1,
    )

    records = ncbi_client.fetch_sra_records(ids)

    assert isinstance(records, str)
    assert len(records) > 0


def test_parse_sra_records():
    ids = ncbi_client.search_sra(
        "Alzheimer disease AND Homo sapiens AND RNA-Seq",
        retmax=2,
    )

    records = ncbi_client.fetch_sra_records(ids)
    datasets = ncbi_client.parse_sra_records(records)

    assert isinstance(datasets, list)
    assert len(datasets) > 0

    dataset = datasets[0]

    assert dataset.accession
    assert dataset.library_strategy
def test_alzheimer_metadata():
    ids = ncbi_client.search_sra(
        "Alzheimer disease AND Homo sapiens AND RNA-Seq",
        retmax=1,
    )

    records = ncbi_client.fetch_sra_records(ids)
    datasets = ncbi_client.parse_sra_records(records)

    dataset = datasets[0]

    assert dataset.organism == "Homo sapiens"
    assert dataset.study_accession
    assert dataset.study_title
    assert dataset.study_abstract
    assert dataset.sample_count is not None
    assert dataset.run_count is not None
    assert dataset.experiment_type


def test_arabidopsis_metadata():
    ids = ncbi_client.search_sra(
        "Arabidopsis thaliana AND RNA-Seq",
        retmax=1,
    )

    records = ncbi_client.fetch_sra_records(ids)
    datasets = ncbi_client.parse_sra_records(records)

    dataset = datasets[0]

    assert dataset.organism == "Arabidopsis thaliana"
    assert dataset.study_accession
    assert dataset.library_strategy == "RNA-Seq"
    assert dataset.sample_count is not None
    assert dataset.run_count is not None