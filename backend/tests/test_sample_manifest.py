
import gzip

from app.services.geo_expression_service import GeoSeriesMatrix
from app.analysis.sample_manifest import build_geo_sample_manifest


def make_matrix(metadata_lines: str) -> GeoSeriesMatrix:
    text = (
        metadata_lines
        + "!series_matrix_table_begin\n"
        + "ID_REF\tGSM10001\tGSM10002\tGSM10003\tGSM10004\n"
        + "probe1\t2.1\t3.4\t5.0\t4.8\n"
        + "!series_matrix_table_end\n"
    )
    payload = gzip.compress(text.encode("utf-8"))

    return GeoSeriesMatrix(
        accession="GSE10072",
        source_url="https://example.test/matrix.gz",
        title="Example study",
        sample_accessions=(
            "GSM10001",
            "GSM10002",
            "GSM10003",
            "GSM10004",
        ),
        matrix_rows=1,
        matrix_columns=4,
        compressed_bytes=len(payload),
        sha256="0" * 64,
        accessed_at="2026-10-18T00:00:00Z",
        retrieved_at="2026-10-18T00:00:00Z",
        cache_hit=False,
        payload=payload,
    )


def test_extracts_structured_samples_and_candidate_pairs():
    matrix = make_matrix(
        '!Sample_geo_accession\t"GSM10001"\t"GSM10002"\t'
        '"GSM10003"\t"GSM10004"\n'
        '!Sample_title\t"Lung Tumor_GT00006"\t'
        '"Normal Lung_GT00006"\t"Lung Tumor_GT00007"\t'
        '"Normal Lung_GT00007"\n'
    )

    result = build_geo_sample_manifest(matrix)

    assert result["sample_count"] == 4
    assert result["pairing_approved"] is False
    assert len(result["pairing_candidates"]) == 2

    first_pair = result["pairing_candidates"][0]
    assert first_pair["patient_id_candidate"] == "GT00006"
    assert first_pair["status"] == "requires_researcher_confirmation"


def test_does_not_invent_pairs_when_patient_ids_are_missing():
    matrix = make_matrix(
        '!Sample_geo_accession\t"GSM10001"\t"GSM10002"\t'
        '"GSM10003"\t"GSM10004"\n'
        '!Sample_title\t"Tumour A"\t"Normal A"\t'
        '"Tumour B"\t"Normal B"\n'
    )

    result = build_geo_sample_manifest(matrix)

    assert result["pairing_candidates"] == []
    assert result["pairing_approved"] is False
    assert any("does not prove samples are unpaired" in warning
               for warning in result["warnings"])


def test_uses_explicit_patient_characteristics():
    matrix = make_matrix(
        '!Sample_geo_accession\t"GSM10001"\t"GSM10002"\t'
        '"GSM10003"\t"GSM10004"\n'
        '!Sample_title\t"Tumour sample"\t"Normal sample"\t'
        '"Tumour sample 2"\t"Normal sample 2"\n'
        '!Sample_characteristics_ch1\t"patient id: P01"\t'
        '"patient id: P01"\t"patient id: P02"\t"patient id: P02"\n'
    )

    result = build_geo_sample_manifest(matrix)

    assert len(result["pairing_candidates"]) == 2
    assert all(
        pair["status"] == "requires_researcher_confirmation"
        for pair in result["pairing_candidates"]
    )
