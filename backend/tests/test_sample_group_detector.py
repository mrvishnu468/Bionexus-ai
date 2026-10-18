from app.models.sample_groups import GroupDetectionStatus
from app.services.sample_group_detector import sample_group_detector


def test_detects_control_and_disease_groups():
    samples = [
        {
            "accession": "SRS001",
            "attributes": {"condition": "control"},
        },
        {
            "accession": "SRS002",
            "attributes": {"condition": "control"},
        },
        {
            "accession": "SRS003",
            "attributes": {"condition": "disease"},
        },
        {
            "accession": "SRS004",
            "attributes": {"condition": "disease"},
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.CONFIRMED
    assert len(result.groups) == 2

    control = next(
        group for group in result.groups
        if group.name == "Control"
    )

    disease = next(
        group for group in result.groups
        if group.name == "Disease"
    )

    assert control.sample_accessions == ["SRS001", "SRS002"]
    assert disease.sample_accessions == ["SRS003", "SRS004"]


def test_single_group_is_candidate():
    samples = [
        {
            "accession": "SRS010",
            "attributes": {"group": "disease"},
        },
        {
            "accession": "SRS011",
            "attributes": {"group": "disease"},
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.CANDIDATE
    assert len(result.groups) == 1
    assert result.groups[0].name == "Disease"


def test_missing_group_metadata_is_unknown():
    samples = [
        {
            "accession": "SRS020",
            "attributes": {
                "age": "71",
                "sex": "male",
                "tissue": "V1",
            },
        },
        {
            "accession": "SRS021",
            "attributes": {
                "age": "68",
                "sex": "female",
                "tissue": "V1",
            },
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.UNKNOWN
    assert len(result.groups) == 0
    assert len(result.warnings) >= 1


def test_preserves_sample_accessions():
    samples = [
        {
            "accession": "SRS100",
            "attributes": {"disease_status": "control"},
        },
        {
            "accession": "SRS101",
            "attributes": {"disease_status": "case"},
        },
    ]

    result = sample_group_detector.detect(samples)

    accessions = [
        accession
        for group in result.groups
        for accession in group.sample_accessions
    ]

    assert accessions == ["SRS100", "SRS101"]
def test_normalizes_group_field_names():
    samples = [
        {
            "accession": "SRS200",
            "attributes": {"disease_status": "healthy control"},
        },
        {
            "accession": "SRS201",
            "attributes": {"disease-status": "Alzheimer's disease"},
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.CONFIRMED
    assert {group.name for group in result.groups} == {
        "Control",
        "Disease",
    }


def test_recognizes_common_control_terms():
    samples = [
        {
            "accession": "SRS210",
            "attributes": {"condition": "normal"},
        },
        {
            "accession": "SRS211",
            "attributes": {"condition": "unaffected"},
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.CANDIDATE
    assert result.groups[0].name == "Control"


def test_recognizes_common_disease_terms():
    samples = [
        {
            "accession": "SRS220",
            "attributes": {"diagnosis": "patient"},
        },
        {
            "accession": "SRS221",
            "attributes": {"diagnosis": "dementia"},
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.CANDIDATE
    assert result.groups[0].name == "Disease"


def test_does_not_infer_group_from_unrelated_metadata():
    samples = [
        {
            "accession": "SRS230",
            "attributes": {
                "age": "71",
                "sex": "male",
                "tissue": "V1",
            },
        },
        {
            "accession": "SRS231",
            "attributes": {
                "age": "68",
                "sex": "female",
                "tissue": "V1",
            },
        },
    ]

    result = sample_group_detector.detect(samples)

    assert result.status == GroupDetectionStatus.UNKNOWN
    assert result.groups == []


def test_preserves_distinct_named_experimental_groups():
    samples = [
        {
            "accession": "SRS301",
            "attributes": {"condition": "early breast cancer"},
        },
        {
            "accession": "SRS302",
            "attributes": {"condition": "advanced breast cancer"},
        },
        {
            "accession": "SRS303",
            "attributes": {"condition": "benign breast tumor"},
        },
        {
            "accession": "SRS304",
            "attributes": {
                "condition": "matched adjacent non-tumor tissue"
            },
        },
    ]

    result = sample_group_detector.detect(samples)

    assert len(result.groups) == 4
    assert {group.name for group in result.groups} == {
        "early breast cancer",
        "advanced breast cancer",
        "benign breast tumor",
        "matched adjacent non-tumor tissue",
    }
    assert all(
        group.confidence < 1.0
        for group in result.groups
    )


def test_adjacent_non_tumor_tissue_is_not_assumed_healthy():
    samples = [
        {
            "accession": "SRS310",
            "attributes": {
                "condition": "matched adjacent non-tumor tissue"
            },
        },
        {
            "accession": "SRS311",
            "attributes": {
                "condition": "early breast cancer"
            },
        },
    ]

    result = sample_group_detector.detect(samples)

    assert "Control" not in {group.name for group in result.groups}
    assert "Disease" not in {group.name for group in result.groups}
