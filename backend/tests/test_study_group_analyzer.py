from app.models.sample_groups import GroupDetectionStatus
from app.services.study_group_analyzer import (
    study_group_analyzer,
)


def test_analyzes_real_study_groups():
    result = study_group_analyzer.analyze(
        "SRP415133",
        retmax=10,
    )

    assert result is not None
    assert result.status in {
        GroupDetectionStatus.CONFIRMED,
        GroupDetectionStatus.CANDIDATE,
        GroupDetectionStatus.UNKNOWN,
    }

    assert isinstance(result.groups, list)
    assert isinstance(result.warnings, list)


def test_unknown_study_returns_unknown():
    result = study_group_analyzer.analyze(
        "SRP_DOES_NOT_EXIST",
        retmax=10,
    )

    assert result.status == GroupDetectionStatus.UNKNOWN
    assert result.groups == []