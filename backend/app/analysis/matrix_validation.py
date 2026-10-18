
from __future__ import annotations

import gzip
import io
import math
import re
from collections import Counter
from typing import Any

from app.services.geo_expression_service import (
    GeoRetrievalError,
    GeoSeriesMatrix,
)


_MISSING_VALUES = {"", "na", "n/a", "nan", "null", "none"}
_SAMPLE_ID_PATTERN = re.compile(r"^GSM\d+$", re.IGNORECASE)

_TUMOUR_PATTERN = re.compile(
    r"\b(tumou?r|cancer|carcinoma|adenocarcinoma|malignan(?:t|cy))\b",
    re.IGNORECASE,
)
_NORMAL_PATTERN = re.compile(
    r"\b(normal|healthy|control|non[- ]tumou?r|"
    r"non[- ]cancerous|benign)\b",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    return value.strip().strip('"').strip()


def _classify_sample(metadata: str) -> str | None:
    """Infer a broad group only when metadata contains clear evidence."""
    tumour = bool(_TUMOUR_PATTERN.search(metadata))
    normal = bool(_NORMAL_PATTERN.search(metadata))

    if tumour and not normal:
        return "Tumour"

    if normal and not tumour:
        return "Normal"

    return None


def validate_geo_matrix(matrix: GeoSeriesMatrix) -> dict[str, Any]:
    """Validate a retrieved GEO matrix without loading its full text at once."""
    errors: list[str] = []
    warnings: list[str] = []

    if not matrix.payload:
        raise GeoRetrievalError("The retrieved matrix payload is empty.")

    try:
        stream = io.TextIOWrapper(
            gzip.GzipFile(fileobj=io.BytesIO(matrix.payload)),
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, EOFError) as exc:
        raise GeoRetrievalError(
            "The retrieved matrix could not be opened."
        ) from exc

    sample_accessions: tuple[str, ...] = ()
    sample_metadata: list[str] = []
    platform_ids: set[str] = set()
    header: list[str] | None = None
    table_started = False
    table_ended = False

    row_count = 0
    missing_values = 0
    invalid_numeric_values = 0
    non_finite_values = 0
    negative_values = 0
    non_integer_values = 0
    observed_values = 0
    minimum_value: float | None = None
    maximum_value: float | None = None
    feature_ids: set[str] = set()
    duplicate_feature_ids = 0
    ragged_rows = 0
    group_counts: Counter[str] = Counter()
    sample_group_evidence: Counter[str] = Counter()

    try:
        for raw_line in stream:
            line = raw_line.rstrip("\r\n")

            if not table_started:
                if line.startswith("!Sample_geo_accession"):
                    sample_accessions = tuple(
                        _clean(value)
                        for value in line.split("\t")[1:]
                        if _clean(value)
                    )

                elif line.startswith("!Sample_platform_id"):
                    platform_ids.update(
                        _clean(value)
                        for value in line.split("\t")[1:]
                        if _clean(value)
                    )

                elif line.startswith("!Sample_title"):
                    values = [_clean(v) for v in line.split("\t")[1:]]
                    sample_metadata = [
                        " ".join(values[i:i + 1])
                        for i in range(len(values))
                    ]

                elif line.startswith("!Sample_source_name_ch1"):
                    values = [_clean(v) for v in line.split("\t")[1:]]
                    if len(values) == len(sample_accessions):
                        for index, value in enumerate(values):
                            sample_metadata[index] += " " + value

                elif line.startswith("!Sample_characteristics_ch"):
                    values = [_clean(v) for v in line.split("\t")[1:]]
                    if len(values) == len(sample_accessions):
                        for index, value in enumerate(values):
                            if index < len(sample_metadata):
                                sample_metadata[index] += " " + value

                elif line.startswith("!series_matrix_table_begin"):
                    table_started = True
                    continue

                continue

            if line.startswith("!series_matrix_table_end"):
                table_ended = True
                break

            if not line.strip():
                continue

            cells = line.split("\t")

            if header is None:
                header = [_clean(value) for value in cells]

                if len(header) < 3:
                    errors.append(
                        "The expression table must contain a feature "
                        "column and at least two sample columns."
                    )
                    continue

                matrix_sample_ids = header[1:]

                if len(set(matrix_sample_ids)) != len(matrix_sample_ids):
                    errors.append(
                        "The expression table contains duplicate sample IDs."
                    )

                if len(set(sample_accessions)) != len(sample_accessions):
                    errors.append(
                        "The GEO sample metadata contains duplicate accessions."
                    )

                if tuple(matrix_sample_ids) != sample_accessions:
                    errors.append(
                        "Matrix sample IDs do not exactly match the GEO "
                        "sample accession metadata in the same order."
                    )

                continue

            row_count += 1

            if len(cells) != len(header):
                ragged_rows += 1
                continue

            feature_id = _clean(cells[0])

            if not feature_id:
                errors.append(
                    f"Expression row {row_count} has an empty feature ID."
                )
            elif feature_id in feature_ids:
                duplicate_feature_ids += 1
            else:
                feature_ids.add(feature_id)

            for raw_value in cells[1:]:
                value_text = _clean(raw_value)

                if value_text.lower() in _MISSING_VALUES:
                    missing_values += 1
                    continue

                try:
                    value = float(value_text)
                except ValueError:
                    invalid_numeric_values += 1
                    continue

                if not math.isfinite(value):
                    non_finite_values += 1
                    continue

                observed_values += 1
                minimum_value = (
                    value if minimum_value is None
                    else min(minimum_value, value)
                )
                maximum_value = (
                    value if maximum_value is None
                    else max(maximum_value, value)
                )

                if value < 0:
                    negative_values += 1

                if not value.is_integer():
                    non_integer_values += 1

    except (OSError, EOFError, UnicodeDecodeError) as exc:
        raise GeoRetrievalError(
            "The GEO matrix could not be fully decompressed and read."
        ) from exc
    finally:
        stream.close()

    if not table_started or header is None:
        errors.append("The GEO expression table or its header is missing.")

    if not table_ended:
        errors.append("The GEO expression table end marker is missing.")

    if not sample_accessions:
        errors.append("No GEO sample accession metadata was found.")

    if row_count == 0:
        errors.append("The expression table contains no data rows.")

    if ragged_rows:
        errors.append(
            f"{ragged_rows} expression rows have inconsistent column counts."
        )

    if duplicate_feature_ids:
        warnings.append(
            f"{duplicate_feature_ids} duplicate feature IDs were found. "
            "Gene-level aggregation has not been performed."
        )

    if missing_values:
        warnings.append(
            f"The matrix contains {missing_values} missing expression values."
        )

    if invalid_numeric_values:
        errors.append(
            f"{invalid_numeric_values} expression values are not numeric."
        )

    if non_finite_values:
        errors.append(
            f"{non_finite_values} expression values are not finite numbers."
        )

    if observed_values and negative_values == 0:
        if non_integer_values == 0:
            representation = "nonnegative_integer_values"
        else:
            representation = "nonnegative_continuous_values"
    elif observed_values:
        representation = "continuous_values_with_negatives"
    else:
        representation = "undetermined"

    if representation == "nonnegative_integer_values":
        warnings.append(
            "Values are nonnegative integers, but this alone does not prove "
            "they are raw RNA-seq counts."
        )
    elif representation == "nonnegative_continuous_values":
        warnings.append(
            "Values are continuous. Confirm the assay, normalization, "
            "and transformation before selecting an analysis method."
        )

    if not platform_ids:
        warnings.append(
            "Platform metadata was not available in the inspected matrix."
        )

    if sample_metadata and len(sample_metadata) == len(sample_accessions):
        for metadata in sample_metadata:
            group = _classify_sample(metadata)
            if group:
                group_counts[group] += 1
                sample_group_evidence[group] += 1
    else:
        warnings.append(
            "Complete per-sample titles or metadata were unavailable for "
            "automatic sample-group inference."
        )

    if not group_counts:
        warnings.append(
            "Tumour and normal groups could not be inferred confidently "
            "from the available sample metadata."
        )
    elif not {"Tumour", "Normal"}.issubset(group_counts):
        warnings.append(
            "Both tumour and normal groups were not identified. "
            "Review the sample annotations before differential expression."
        )

    if len(platform_ids) > 1:
        warnings.append(
            "Multiple platform IDs were found. Confirm platform compatibility "
            "before combining samples."
        )

    if header is not None and len(sample_accessions) != len(header) - 1:
        warnings.append(
            "The sample metadata count differs from the expression "
            "table's sample-column count."
        )

    ready = not errors
    status = "blocked" if errors else (
        "review_required" if warnings else "passed"
    )

    return {
        "accession": matrix.accession,
        "title": matrix.title,
        "status": status,
        "ready_for_design_review": ready,
        "assay_type": "not_confirmed_from_matrix_alone",
        "data_representation": representation,
        "platform_ids": sorted(platform_ids),
        "matrix_rows": row_count,
        "matrix_columns": max(len(header or []) - 1, 0),
        "metadata_sample_count": len(sample_accessions),
        "sample_ids_aligned": (
            header is not None
            and tuple(header[1:]) == sample_accessions
        ),
        "duplicate_feature_ids": duplicate_feature_ids,
        "ragged_rows": ragged_rows,
        "missing_values": missing_values,
        "invalid_numeric_values": invalid_numeric_values,
        "non_finite_values": non_finite_values,
        "observed_values": observed_values,
        "minimum_value": minimum_value,
        "maximum_value": maximum_value,
        "negative_values": negative_values,
        "non_integer_values": non_integer_values,
        "inferred_sample_groups": dict(group_counts),
        "sample_group_evidence": dict(sample_group_evidence),
        "errors": errors,
        "warnings": warnings,
    }
