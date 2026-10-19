
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.analysis.geo_analysis_pipeline import GeoAnalysisPipelineError
from app.services.geo_expression_service import GeoRetrievalError
from app.tools.ncbi.geo_link_resolver import GeoLinkResolution


client = TestClient(app)


def test_prepare_analysis_returns_review_package():
    review_package = {
        "accession": "GSE10072",
        "title": "Synthetic test dataset",
        "status": "needs_design_review",
        "analysis_executed": False,
        "design_review": {
            "status": "needs_design_review",
            "approved": False,
            "assignments": [],
            "suggestions": [],
            "pairings": [],
            "pairing_approved": False,
            "warnings": [],
        },
    }

    with (
        patch("app.api.geo.get_geo_service"),
        patch(
            "app.api.geo.prepare_geo_analysis",
            new_callable=AsyncMock,
            return_value=review_package,
        ) as prepare,
    ):
        response = client.post(
            "/api/geo/prepare-analysis",
            json={"accession": "GSE10072"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_design_review"
    assert body["analysis_executed"] is False
    prepare.assert_awaited_once()


def test_prepare_analysis_returns_422_when_matrix_is_blocked():
    with (
        patch("app.api.geo.get_geo_service"),
        patch(
            "app.api.geo.prepare_geo_analysis",
            new_callable=AsyncMock,
            side_effect=GeoAnalysisPipelineError(
                "GEO matrix validation blocked analysis preparation."
            ),
        ),
    ):
        response = client.post(
            "/api/geo/prepare-analysis",
            json={"accession": "GSE10072"},
        )

    assert response.status_code == 422
    assert "validation blocked" in response.json()["detail"]


def test_prepare_analysis_returns_502_when_retrieval_fails():
    with (
        patch("app.api.geo.get_geo_service"),
        patch(
            "app.api.geo.prepare_geo_analysis",
            new_callable=AsyncMock,
            side_effect=GeoRetrievalError(
                "Upstream GEO service unavailable"
            ),
        ),
    ):
        response = client.post(
            "/api/geo/prepare-analysis",
            json={"accession": "GSE10072"},
        )

    assert response.status_code == 502
    assert (
        "GEO analysis preparation failed"
        in response.json()["detail"]
    )


def test_prepare_analysis_rejects_invalid_accession():
    response = client.post(
        "/api/geo/prepare-analysis",
        json={"accession": "INVALID"},
    )

    assert response.status_code == 422


def test_retrieve_returns_geo_metadata():
    geo_result = SimpleNamespace(
        accession="GSE10072",
        title="Synthetic test dataset",
        source_url=(
            "https://ftp.ncbi.nlm.nih.gov/geo/series/"
            "GSE10nnn/GSE10072/matrix/GSE10072_series_matrix.txt.gz"
        ),
        sample_accessions=("GSM100001", "GSM100002"),
        matrix_rows=100,
        matrix_columns=2,
        compressed_bytes=512,
        sha256="a" * 64,
        accessed_at="2026-10-18T07:00:00+00:00",
        retrieved_at=None,
        cache_hit=True,
    )

    with patch("app.api.geo.get_geo_service") as get_service:
        get_service.return_value.fetch = AsyncMock(
            return_value=geo_result
        )

        response = client.post(
            "/api/geo/retrieve",
            json={"accession": "GSE10072"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["accession"] == "GSE10072"
    assert body["matrix_columns"] == 2
    assert body["cache_hit"] is True
    assert body["retrieved_at"] is None


def test_resolve_sra_returns_unconfirmed_candidate():
    resolution = GeoLinkResolution(
        study_accession="SRP123456",
        status="resolved",
        geo_accessions=("GSE10072",),
        message="One GEO Series was returned by the NCBI link lookup.",
    )

    with patch(
        "app.api.geo.geo_link_resolver.resolve",
        return_value=resolution,
    ):
        response = client.post(
            "/api/geo/resolve-sra",
            json={"study_accession": "SRP123456"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "candidate"
    assert body["geo_accessions"] == ["GSE10072"]
    assert body["mapping_confirmed"] is False
    assert body["analysis_ready"] is False


def test_resolve_sra_keeps_ambiguous_mapping_unconfirmed():
    resolution = GeoLinkResolution(
        study_accession="SRP123456",
        status="ambiguous",
        geo_accessions=("GSE10072", "GSE20000"),
        message="Multiple linked GEO Series require researcher review.",
    )

    with patch(
        "app.api.geo.geo_link_resolver.resolve",
        return_value=resolution,
    ):
        response = client.post(
            "/api/geo/resolve-sra",
            json={"study_accession": "SRP123456"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ambiguous"
    assert len(body["geo_accessions"]) == 2
    assert body["mapping_confirmed"] is False
    assert body["analysis_ready"] is False


def test_resolve_sra_returns_502_on_ncbi_failure():
    with patch(
        "app.api.geo.geo_link_resolver.resolve",
        side_effect=RuntimeError("NCBI unavailable"),
    ):
        response = client.post(
            "/api/geo/resolve-sra",
            json={"study_accession": "SRP123456"},
        )

    assert response.status_code == 502


def test_resolve_sra_rejects_invalid_accession():
    response = client.post(
        "/api/geo/resolve-sra",
        json={"study_accession": "GSE10072"},
    )

    assert response.status_code == 422
