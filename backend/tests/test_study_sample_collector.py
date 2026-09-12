from app.services.study_sample_collector import (
    study_sample_collector,
)


def test_collects_samples_from_real_study():
    samples = study_sample_collector.collect(
        "SRP415133",
        retmax=10,
    )

    assert samples
    assert all(
        sample["study_accession"] == "SRP415133"
        for sample in samples
    )

    assert all(
        sample["experiment_accession"]
        for sample in samples
    )

    assert all(
        sample["accession"]
        for sample in samples
    )


def test_collect_returns_empty_for_unknown_study():
    samples = study_sample_collector.collect(
        "SRP_DOES_NOT_EXIST",
        retmax=10,
    )

    assert samples == []