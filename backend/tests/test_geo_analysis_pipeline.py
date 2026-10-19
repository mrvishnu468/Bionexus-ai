
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.analysis.geo_analysis_pipeline import (
    GeoAnalysisPipelineError,
    prepare_geo_analysis,
)


def make_matrix():
    return SimpleNamespace(
        accession="GSE10072",
        title="Synthetic test dataset",
        source_url="https://example.org/GSE10072",
        sha256="test-sha256",
        cache_hit=True,
        accessed_at=None,
        retrieved_at=None,
        sample_accessions=("GSM1", "GSM2"),
    )


def make_manifest():
    return {
        "accession": "GSE10072",
        "samples": [
            {
                "accession": "GSM1",
                "inferred_group": "Normal",
                "group_evidence": ["synthetic evidence"],
            },
            {
                "accession": "GSM2",
                "inferred_group": "Tumour",
                "group_evidence": ["synthetic evidence"],
            },
        ],
        "pairing_candidates": [],
        "warnings": [],
    }


def make_expression(sample_accessions=("GSM1", "GSM2")):
    return SimpleNamespace(
        sample_accessions=sample_accessions,
        summary=lambda: {
            "accession": "GSE10072",
            "feature_count": 5,
            "sample_count": len(sample_accessions),
            "sample_accessions": list(sample_accessions),
        },
    )


def test_preparation_requires_design_review():
    service = SimpleNamespace(
        fetch=AsyncMock(return_value=make_matrix())
    )

    async def scenario():
        with (
            patch(
                "app.analysis.geo_analysis_pipeline.validate_geo_matrix",
                return_value={"status": "valid"},
            ),
            patch(
                "app.analysis.geo_analysis_pipeline.build_geo_sample_manifest",
                return_value=make_manifest(),
            ),
            patch(
                "app.analysis.geo_analysis_pipeline.parse_geo_expression_matrix",
                return_value=make_expression(),
            ),
        ):
            result = await prepare_geo_analysis(
                "GSE10072", geo_service=service
            )

        assert result["analysis_status"] == "needs_design_review"
        assert result["analysis_executed"] is False
        assert result["design_review"]["approved"] is False
        assert result["design_review"]["pairing_approved"] is False
        assert all(
            item["confirmed_group"] is None
            for item in result["design_review"]["group_assignments"]
        )
        service.fetch.assert_awaited_once()

    asyncio.run(scenario())


def test_preparation_rejects_sample_mismatch():
    service = SimpleNamespace(
        fetch=AsyncMock(return_value=make_matrix())
    )

    async def scenario():
        with (
            patch(
                "app.analysis.geo_analysis_pipeline.validate_geo_matrix",
                return_value={"status": "valid"},
            ),
            patch(
                "app.analysis.geo_analysis_pipeline.build_geo_sample_manifest",
                return_value=make_manifest(),
            ),
            patch(
                "app.analysis.geo_analysis_pipeline.parse_geo_expression_matrix",
                return_value=make_expression(("GSM1", "GSM_OTHER")),
            ),
        ):
            with pytest.raises(
                GeoAnalysisPipelineError,
                match="do not align",
            ):
                await prepare_geo_analysis(
                    "GSE10072", geo_service=service
                )

    asyncio.run(scenario())


def test_preparation_rejects_blocked_matrix():
    service = SimpleNamespace(
        fetch=AsyncMock(return_value=make_matrix())
    )

    async def scenario():
        with patch(
            "app.analysis.geo_analysis_pipeline.validate_geo_matrix",
            return_value={"status": "blocked"},
        ):
            with pytest.raises(
                GeoAnalysisPipelineError,
                match="validation blocked",
            ):
                await prepare_geo_analysis(
                    "GSE10072", geo_service=service
                )

    asyncio.run(scenario())
