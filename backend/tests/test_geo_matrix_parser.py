
import gzip
import hashlib

import pytest

from app.analysis.geo_matrix_parser import (
    GeoMatrixParseError,
    parse_geo_expression_matrix,
)
from app.services.geo_expression_service import GeoSeriesMatrix


def make_matrix(table: str) -> GeoSeriesMatrix:
    payload = gzip.compress(table.encode("utf-8"))
    return GeoSeriesMatrix(
        accession="GSE_TEST",
        source_url="https://example.org/test_matrix.txt.gz",
        title="Synthetic test matrix",
        sample_accessions=("GSM2", "GSM1"),
        matrix_rows=2,
        matrix_columns=2,
        compressed_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        accessed_at="2026-01-01T00:00:00+00:00",
        retrieved_at="2026-01-01T00:00:00+00:00",
        cache_hit=False,
        payload=payload,
    )


def table_with(rows: str) -> str:
    return (
        '!Sample_geo_accession\t"GSM2"\t"GSM1"\n'
        "!series_matrix_table_begin\n"
        '"ID_REF"\t"GSM1"\t"GSM2"\n'
        f"{rows}"
        "!series_matrix_table_end\n"
    )


def test_parser_reads_values_and_aligns_sample_order():
    matrix = make_matrix(
        table_with('"GENE_A"\t10\t20\n"GENE_B"\t3\t7\n')
    )

    result = parse_geo_expression_matrix(matrix)

    assert result.feature_ids == ("GENE_A", "GENE_B")
    assert result.sample_accessions == ("GSM2", "GSM1")
    assert result.values == ((20.0, 10.0), (7.0, 3.0))
    assert result.matrix_rows == 2
    assert result.matrix_columns == 2


def test_parser_rejects_duplicate_feature_ids():
    matrix = make_matrix(
        table_with('"GENE_A"\t1\t2\n"GENE_A"\t3\t4\n')
    )

    with pytest.raises(GeoMatrixParseError, match="Duplicate feature"):
        parse_geo_expression_matrix(matrix)


def test_parser_rejects_mismatched_sample_columns():
    matrix = make_matrix(
        '!series_matrix_table_begin\n'
        '"ID_REF"\t"GSM1"\t"GSM3"\n'
        '"GENE_A"\t1\t2\n'
        "!series_matrix_table_end\n"
    )

    with pytest.raises(GeoMatrixParseError, match="do not match"):
        parse_geo_expression_matrix(matrix)


@pytest.mark.parametrize("bad_value", ["not-a-number", "NaN", "Inf", "-Inf"])
def test_parser_rejects_invalid_expression_values(bad_value):
    matrix = make_matrix(
        table_with(f'"GENE_A"\t1\t{bad_value}\n')
    )

    with pytest.raises(GeoMatrixParseError):
        parse_geo_expression_matrix(matrix)


def test_parser_rejects_incomplete_table():
    matrix = make_matrix(
        '!Sample_geo_accession\t"GSM2"\t"GSM1"\n'
        "!series_matrix_table_begin\n"
        '"ID_REF"\t"GSM1"\t"GSM2"\n'
        '"GENE_A"\t1\t2\n'
    )

    with pytest.raises(GeoMatrixParseError, match="no complete"):
        parse_geo_expression_matrix(matrix)
