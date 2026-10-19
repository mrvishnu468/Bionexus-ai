
from __future__ import annotations

import csv
import gzip
import io
import math
from dataclasses import dataclass
from typing import Any

from app.services.geo_expression_service import (
    GeoRetrievalError,
    GeoSeriesMatrix,
)


_TABLE_BEGIN = "!series_matrix_table_begin"
_TABLE_END = "!series_matrix_table_end"


class GeoMatrixParseError(GeoRetrievalError):
    """Raised when a GEO expression table cannot be parsed safely."""


@dataclass(frozen=True)
class ParsedGeoExpression:
    """Parsed numeric expression values with their sample identities."""

    accession: str
    feature_ids: tuple[str, ...]
    sample_accessions: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    source_url: str
    sha256: str
    matrix_rows: int
    matrix_columns: int

    def summary(self) -> dict[str, Any]:
        """Return metadata without exposing the full expression matrix."""
        return {
            "accession": self.accession,
            "source_url": self.source_url,
            "sha256": self.sha256,
            "feature_count": self.matrix_rows,
            "sample_count": self.matrix_columns,
            "sample_accessions": list(self.sample_accessions),
        }


def parse_geo_expression_matrix(
    matrix: GeoSeriesMatrix,
) -> ParsedGeoExpression:
    """Parse a processed GEO Series Matrix into a numeric expression matrix."""
    try:
        text = gzip.decompress(matrix.payload).decode("utf-8")
    except (gzip.BadGzipFile, EOFError, OSError, UnicodeDecodeError) as exc:
        raise GeoMatrixParseError(
            "The GEO payload could not be decompressed as UTF-8."
        ) from exc

    lines = text.splitlines()
    table_start: int | None = None
    table_end: int | None = None

    for index, line in enumerate(lines):
        if line.strip() == _TABLE_BEGIN:
            table_start = index + 1
        elif line.strip() == _TABLE_END:
            table_end = index
            break

    if table_start is None or table_end is None:
        raise GeoMatrixParseError(
            "The GEO payload has no complete expression table."
        )

    table_lines = [
        line for line in lines[table_start:table_end] if line.strip()
    ]
    if len(table_lines) < 2:
        raise GeoMatrixParseError(
            "The GEO expression table has no feature rows."
        )

    try:
        reader = csv.reader(table_lines, delimiter="\t", strict=True)
        header = next(reader)
        rows = list(reader)
    except (csv.Error, StopIteration) as exc:
        raise GeoMatrixParseError(
            "The GEO expression table is malformed."
        ) from exc

    if len(header) < 3:
        raise GeoMatrixParseError(
            "The table must contain a feature identifier and at least "
            "two sample columns."
        )

    header = [value.strip().strip('"') for value in header]
    feature_column = header[0]
    sample_accessions = tuple(header[1:])

    if not feature_column:
        raise GeoMatrixParseError("The feature identifier column is empty.")

    if any(not sample for sample in sample_accessions):
        raise GeoMatrixParseError("A sample accession is empty.")

    if len(set(sample_accessions)) != len(sample_accessions):
        raise GeoMatrixParseError(
            "The expression table contains duplicate sample columns."
        )

    expected_samples = tuple(matrix.sample_accessions)
    if (
        len(set(expected_samples)) != len(expected_samples)
        or set(sample_accessions) != set(expected_samples)
    ):
        raise GeoMatrixParseError(
            "Expression columns do not match the GEO sample accessions."
        )

    sample_positions = {
        sample: index for index, sample in enumerate(sample_accessions)
    }
    reorder = [sample_positions[sample] for sample in expected_samples]

    feature_ids: list[str] = []
    expression_rows: list[tuple[float, ...]] = []
    seen_features: set[str] = set()

    for line_number, row in enumerate(rows, start=2):
        if len(row) != len(header):
            raise GeoMatrixParseError(
                f"Feature row {line_number} has {len(row)} fields; "
                f"expected {len(header)}."
            )

        feature_id = row[0].strip().strip('"')
        if not feature_id:
            raise GeoMatrixParseError(
                f"Feature row {line_number} has an empty identifier."
            )

        if feature_id in seen_features:
            raise GeoMatrixParseError(
                f"Duplicate feature identifier: {feature_id}"
            )

        parsed_values: list[float] = []
        for raw_value in row[1:]:
            value_text = raw_value.strip().strip('"')

            try:
                value = float(value_text)
            except ValueError as exc:
                raise GeoMatrixParseError(
                    f"Invalid expression value in feature {feature_id}."
                ) from exc

            if not math.isfinite(value):
                raise GeoMatrixParseError(
                    f"Non-finite expression value in feature {feature_id}."
                )

            parsed_values.append(value)

        feature_ids.append(feature_id)
        expression_rows.append(
            tuple(parsed_values[index] for index in reorder)
        )
        seen_features.add(feature_id)

    if not expression_rows:
        raise GeoMatrixParseError("No expression values were parsed.")

    return ParsedGeoExpression(
        accession=matrix.accession,
        feature_ids=tuple(feature_ids),
        sample_accessions=expected_samples,
        values=tuple(expression_rows),
        source_url=matrix.source_url,
        sha256=matrix.sha256,
        matrix_rows=len(expression_rows),
        matrix_columns=len(expected_samples),
    )
