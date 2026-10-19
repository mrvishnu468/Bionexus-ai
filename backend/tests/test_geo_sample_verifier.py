
from datetime import datetime, timezone

import pytest

from app.services.geo_sample_verifier import (
    SampleRecord,
    _parse_soft_record,
    verify_pair_records,
)


def sample(accession, title, patient_id, extra=None):
    characteristics = {"patient id": patient_id} if patient_id else {}
    if extra:
        characteristics.update(extra)

    return SampleRecord(
        accession=accession,
        title=title,
        characteristics=characteristics,
        source_url=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


def test_matching_patient_and_roles_are_corroborated_but_not_approved():
    tumour = sample("GSM10001", "Patient P01 tumour", "P01")
    normal = sample("GSM10002", "Patient P01 normal control", "P01")

    result = verify_pair_records(tumour, normal)

    assert result.status == "corroborated"
    assert result.approved is False
    assert result.tumour_accession == "GSM10001"
    assert result.normal_accession == "GSM10002"
    assert result.evidence["tumour_record"]["source_url"]


def test_different_patient_ids_are_conflicting():
    tumour = sample("GSM10001", "P01 tumour", "P01")
    normal = sample("GSM10002", "P02 normal", "P02")

    result = verify_pair_records(tumour, normal)

    assert result.status == "conflicting"
    assert result.approved is False


def test_missing_patient_id_is_ambiguous():
    tumour = sample("GSM10001", "Tumour sample", None)
    normal = sample("GSM10002", "Normal sample", None)

    result = verify_pair_records(tumour, normal)

    assert result.status == "ambiguous"
    assert result.approved is False


def test_conflicting_sample_roles_are_rejected():
    tumour = sample("GSM10001", "Normal tissue", "P01")
    normal = sample("GSM10002", "Tumour tissue", "P01")

    result = verify_pair_records(tumour, normal)

    assert result.status == "conflicting"


def test_multiple_patient_ids_are_ambiguous():
    tumour = sample(
        "GSM10001",
        "Tumour tissue",
        "P01",
        {"subject id": "P02"},
    )
    normal = sample("GSM10002", "Normal tissue", "P01")

    result = verify_pair_records(tumour, normal)

    assert result.status == "ambiguous"


def test_same_accession_cannot_form_a_pair():
    record = sample("GSM10001", "Tumour tissue", "P01")

    result = verify_pair_records(record, record)

    assert result.status == "conflicting"
    assert result.approved is False


def test_soft_parser_preserves_title_and_characteristics():
    text = """^SAMPLE = GSM10001
!Sample_title = Patient P01 tumour
!Sample_characteristics_ch1 = patient id: P01
!Sample_characteristics_ch1 = tissue: tumour
"""

    record = _parse_soft_record(
        "GSM10001",
        text,
        "https://example.org/GSM10001",
    )

    assert record.accession == "GSM10001"
    assert record.title == "Patient P01 tumour"
    assert record.characteristics["patient id"] == "P01"
    assert record.characteristics["tissue"] == "tumour"
    assert record.source_url == "https://example.org/GSM10001"
