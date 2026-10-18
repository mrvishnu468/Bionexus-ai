
import asyncio
import pytest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.study_design import (
    StudyDesignReviewRequest,
    review_study_design,
)
from app.models.sample_groups import (
    DetectedGroup,
    GroupDetectionResult,
    GroupDetectionStatus,
)


def make_group(name, accessions):
    return DetectedGroup(
        name=name,
        sample_accessions=accessions,
        evidence=["Mocked sample metadata"],
        confidence=0.8,
    )


def make_detection(groups, warnings=None):
    if len(groups) >= 2:
        status = GroupDetectionStatus.CONFIRMED
    elif groups:
        status = GroupDetectionStatus.CANDIDATE
    else:
        status = GroupDetectionStatus.UNKNOWN

    return GroupDetectionResult(
        status=status,
        groups=groups,
        warnings=warnings or [],
    )


def test_no_detected_groups_are_rejected():
    with patch(
        "app.api.study_design.study_group_analyzer.analyze",
        return_value=make_detection([]),
    ):
        result = asyncio.run(
            review_study_design(
                StudyDesignReviewRequest(
                    study_accession="SRP_TEST"
                )
            )
        )

    assert result.design_suitable is False
    assert result.group_detection.groups == []
    assert any(
        "could not be established" in reason
        for reason in result.design_reasons
    )


def test_named_tissue_groups_are_not_assumed_controls():
    groups = [
        make_group(
            "early breast cancer",
            ["S1", "S2", "S3"],
        ),
        make_group(
            "matched adjacent non-tumor tissue",
            ["S4", "S5", "S6"],
        ),
    ]

    with patch(
        "app.api.study_design.study_group_analyzer.analyze",
        return_value=make_detection(groups),
    ):
        result = asyncio.run(
            review_study_design(
                StudyDesignReviewRequest(
                    study_accession="SRP_TEST",
                    metadata_complete_confirmed=True,
                    biological_replicates_confirmed=True,
                )
            )
        )

    assert result.design_suitable is False
    assert (
        "No control group is available for comparison."
        in result.design_reasons
    )


def test_confirmed_control_and_disease_pass_preliminary_checks():
    groups = [
        make_group("Control", ["C1", "C2", "C3"]),
        make_group("Disease", ["D1", "D2", "D3"]),
    ]

    with patch(
        "app.api.study_design.study_group_analyzer.analyze",
        return_value=make_detection(groups),
    ):
        result = asyncio.run(
            review_study_design(
                StudyDesignReviewRequest(
                    study_accession="SRP_TEST",
                    metadata_complete_confirmed=True,
                    biological_replicates_confirmed=True,
                )
            )
        )

    assert result.design_suitable is True
    assert result.design_reasons == []


def test_missing_confirmations_keep_design_unsuitable():
    groups = [
        make_group("Control", ["C1", "C2", "C3"]),
        make_group("Disease", ["D1", "D2", "D3"]),
    ]

    with patch(
        "app.api.study_design.study_group_analyzer.analyze",
        return_value=make_detection(groups),
    ):
        result = asyncio.run(
            review_study_design(
                StudyDesignReviewRequest(
                    study_accession="SRP_TEST"
                )
            )
        )

    assert result.design_suitable is False
    assert (
        "Experimental metadata is incomplete."
        in result.design_reasons
    )
    assert (
        "Biological replicates are not confirmed."
        in result.design_reasons
    )


def test_detection_warnings_are_preserved():
    warnings = ["Group labels require researcher review."]
    groups = [
        make_group("Control", ["C1", "C2"]),
        make_group("Disease", ["D1", "D2"]),
    ]

    with patch(
        "app.api.study_design.study_group_analyzer.analyze",
        return_value=make_detection(groups, warnings),
    ):
        result = asyncio.run(
            review_study_design(
                StudyDesignReviewRequest(
                    study_accession="SRP_TEST"
                )
            )
        )

    assert result.group_detection.warnings == warnings


def test_blank_accession_is_rejected():
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            review_study_design(
                StudyDesignReviewRequest(
                    study_accession="   "
                )
            )
        )

    assert error.value.status_code == 422
