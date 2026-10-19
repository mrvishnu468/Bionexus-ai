
import pytest
from Bio import Entrez

from app.tools.ncbi.geo_link_resolver import GeoLinkResolver


class FakeHandle:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def mock_entrez(
    monkeypatch,
    summaries,
    sra_uids=None,
    geo_uids=None,
):
    sra_uids = ["sra1"] if sra_uids is None else sra_uids
    geo_uids = ["geo1"] if geo_uids is None else geo_uids

    monkeypatch.setattr(
        Entrez,
        "esearch",
        lambda **kwargs: FakeHandle({"IdList": sra_uids}),
    )

    link_sets = []
    if geo_uids:
        link_sets = [
            {
                "LinkSetDb": [
                    {
                        "LinkName": "sra_gds",
                        "Link": [{"Id": uid} for uid in geo_uids],
                    }
                ]
            }
        ]

    monkeypatch.setattr(
        Entrez,
        "elink",
        lambda **kwargs: FakeHandle(link_sets),
    )
    monkeypatch.setattr(
        Entrez,
        "esummary",
        lambda **kwargs: FakeHandle(summaries),
    )
    monkeypatch.setattr(Entrez, "read", lambda handle: handle.payload)


def test_resolves_one_directly_linked_geo_series(monkeypatch):
    mock_entrez(monkeypatch, [{"accession": "GSE10072"}])

    result = GeoLinkResolver().resolve("SRP123456")

    assert result.status == "resolved"
    assert result.geo_accessions == ("GSE10072",)


def test_reports_ambiguous_mapping(monkeypatch):
    mock_entrez(
        monkeypatch,
        [
            {"accession": "GSE10072"},
            {"accession": "GSE20000"},
        ],
        geo_uids=["geo1", "geo2"],
    )

    result = GeoLinkResolver().resolve("SRP123456")

    assert result.status == "ambiguous"
    assert result.geo_accessions == ("GSE10072", "GSE20000")


def test_reports_missing_sra_records(monkeypatch):
    mock_entrez(
        monkeypatch,
        [],
        sra_uids=[],
        geo_uids=[],
    )

    result = GeoLinkResolver().resolve("SRP123456")

    assert result.status == "not_found"
    assert result.geo_accessions == ()


def test_reports_missing_geo_links(monkeypatch):
    mock_entrez(monkeypatch, [], geo_uids=[])

    result = GeoLinkResolver().resolve("SRP123456")

    assert result.status == "not_found"
    assert result.geo_accessions == ()


def test_ignores_gds_record_without_gse_accession(monkeypatch):
    mock_entrez(monkeypatch, [{"accession": "GDS123"}])

    result = GeoLinkResolver().resolve("SRP123456")

    assert result.status == "not_found"
    assert result.geo_accessions == ()


def test_rejects_invalid_accession(monkeypatch):
    def unexpected_call(**kwargs):
        pytest.fail("NCBI must not be called for invalid input")

    monkeypatch.setattr(Entrez, "esearch", unexpected_call)

    result = GeoLinkResolver().resolve("GSE10072")

    assert result.status == "invalid"


def test_normalizes_accession_case_and_whitespace(monkeypatch):
    mock_entrez(monkeypatch, [{"accession": "GSE10072"}])

    result = GeoLinkResolver().resolve(" srp123456 ")

    assert result.study_accession == "SRP123456"
    assert result.geo_accessions == ("GSE10072",)



def test_extracts_series_from_ncbi_capitalized_summary_fields(monkeypatch):
    mock_entrez(
        monkeypatch,
        [
            {
                "Accession": "GSM1289256",
                "entryType": "GSM",
                "GSE": "53268;53313",
            },
            {
                "Accession": "GSE53313",
                "entryType": "GSE",
            },
        ],
        geo_uids=["geo1", "geo2"],
    )

    result = GeoLinkResolver().resolve("SRP034076")

    assert result.status == "resolved"
    assert result.geo_accessions == ("GSE53313",)
