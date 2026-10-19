
from __future__ import annotations

from typing import Any

from app.analysis.geo_matrix_parser import (
    ParsedGeoExpression,
    parse_geo_expression_matrix,
)
from app.analysis.matrix_validation import validate_geo_matrix
from app.analysis.sample_manifest import build_geo_sample_manifest
from app.services.geo_expression_service import (
    GeoExpressionService,
    GeoRetrievalError,
)


class GeoAnalysisPipelineError(RuntimeError):
    """Raised when GEO analysis preparation cannot be completed."""


def _validate_sample_alignment(
    manifest: dict[str, Any],
    expression: ParsedGeoExpression,
) -> None:
    """Ensure manifest samples and expression columns identify the same samples."""
    samples = manifest.get("samples", [])
    manifest_accessions = [sample.get("accession") for sample in samples]

    if (
        len(manifest_accessions) != len(set(manifest_accessions))
        or set(manifest_accessions) != set(expression.sample_accessions)
    ):
        raise GeoAnalysisPipelineError(
            "Sample manifest and expression columns do not align."
        )


def _build_design_review(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Expose inferred groups as suggestions, never as approved assignments."""
    samples = manifest.get("samples", [])
    groups: dict[str, list[str]] = {}

    for sample in samples:
        group = sample.get("inferred_group")
        if group:
            groups.setdefault(str(group), []).append(sample["accession"])

    return {
        "status": "needs_design_review",
        "approved": False,
        "group_assignments": [
            {
                "sample_accession": sample["accession"],
                "suggested_group": sample.get("inferred_group"),
                "group_evidence": sample.get("group_evidence", []),
                "confirmed_group": None,
            }
            for sample in samples
        ],
        "suggested_groups": [
            {
                "name": name,
                "sample_accessions": accessions,
            }
            for name, accessions in groups.items()
        ],
        "pairing_candidates": manifest.get("pairing_candidates", []),
        "pairing_approved": False,
        "warnings": manifest.get("warnings", []),
    }


async def prepare_geo_analysis(
    accession: str,
    *,
    geo_service: GeoExpressionService,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Prepare GEO expression data and a researcher-review package.

    This function does not execute statistical analysis. Group assignments,
    contrast direction, and any paired design require explicit approval.
    """
    try:
        matrix = await geo_service.fetch(
            accession,
            force_refresh=force_refresh,
        )
        matrix_validation = validate_geo_matrix(matrix)

        if matrix_validation.get("status") == "blocked":
            raise GeoAnalysisPipelineError(
                "GEO matrix validation blocked analysis preparation."
            )
        manifest = build_geo_sample_manifest(matrix)

        expression = parse_geo_expression_matrix(matrix)
        _validate_sample_alignment(manifest, expression)

    except (GeoRetrievalError, ValueError) as exc:
        raise GeoAnalysisPipelineError(
            f"Could not prepare GEO analysis for {accession}: {exc}"
        ) from exc

    review = _build_design_review(manifest)

    return {
        "accession": matrix.accession,
        "title": matrix.title,
        "source_url": matrix.source_url,
        "provenance": {
            "sha256": matrix.sha256,
            "cache_hit": matrix.cache_hit,
            "accessed_at": matrix.accessed_at,
            "retrieved_at": matrix.retrieved_at,
        },
        "matrix_validation": matrix_validation,
        "expression": expression.summary(),
        "sample_manifest": manifest,
        "design_review": review,
        "analysis_status": "needs_design_review",
        "analysis_executed": False,
    }
