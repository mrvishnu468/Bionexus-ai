
"""Verify candidate patient pairs against individual GEO sample records."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


GEO_SAMPLE_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"


@dataclass(frozen=True)
class SampleRecord:
    accession: str
    title: str | None
    characteristics: dict[str, str]
    source_url: str
    retrieved_at: str


@dataclass(frozen=True)
class PairVerification:
    tumour_accession: str
    normal_accession: str
    status: str
    approved: bool
    evidence: dict[str, Any]


def _parse_soft_record(accession: str, text: str, url: str) -> SampleRecord:
    """Parse the relevant fields from a GEO SOFT sample response."""
    fields: dict[str, list[str]] = {}
    current_characteristic: str | None = None

    for line in text.splitlines():
        if line.startswith("^SAMPLE"):
            if accession not in line.split("=")[-1].strip():
                raise ValueError("GEO response accession does not match request")
        elif line.startswith("!Sample_title"):
            fields.setdefault("title", []).append(
                line.split("=", 1)[-1].strip().strip('"')
            )
        elif line.startswith("!Sample_characteristics_ch1"):
            value = line.split("=", 1)[-1].strip().strip('"')
            if ":" in value:
                key, item = value.split(":", 1)
                current_characteristic = key.strip().casefold()
                fields.setdefault(current_characteristic, []).append(
                    item.strip()
                )
            elif current_characteristic:
                fields.setdefault(current_characteristic, []).append(value)
        elif line.startswith("!Sample_source_name_ch1"):
            fields.setdefault("source_name", []).append(
                line.split("=", 1)[-1].strip().strip('"')
            )

    if not fields:
        raise ValueError("GEO response contains no usable sample metadata")

    characteristics = {
        key: "; ".join(values)
        for key, values in fields.items()
        if key not in {"title", "source_name"}
    }
    title_values = fields.get("title", [])

    return SampleRecord(
        accession=accession,
        title=title_values[0] if title_values else None,
        characteristics=characteristics,
        source_url=url,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


async def fetch_geo_sample(
    accession: str,
    client: httpx.AsyncClient | None = None,
) -> SampleRecord:
    """Fetch one GSM record with bounded network timeouts."""
    if not re.fullmatch(r"GSM\d+", accession.strip(), flags=re.IGNORECASE):
        raise ValueError("Expected a valid GEO sample accession such as GSM12345")

    accession = accession.upper()
    url = GEO_SAMPLE_URL
    params = {"acc": accession, "targ": "self", "form": "text", "view": "full"}

    if client is not None:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return _parse_soft_record(accession, response.text, str(response.url))

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as session:
        response = await session.get(url, params=params)
        response.raise_for_status()
        return _parse_soft_record(accession, response.text, str(response.url))


def _patient_ids(record: SampleRecord) -> set[str]:
    """Extract only explicitly labelled patient identifiers."""
    identifiers: set[str] = set()

    for key, value in record.characteristics.items():
        if re.search(r"\b(patient|subject|individual|participant)\b", key):
            identifiers.update(
                part.strip().casefold()
                for part in re.split(r"[;,]", value)
                if part.strip()
            )

    return identifiers


def _sample_role(record: SampleRecord) -> str | None:
    """Infer a broad sample role from the original record."""
    text = " ".join(
        [record.title or "", *record.characteristics.values()]
    ).casefold()

    tumour = bool(re.search(r"\b(tumou?r|carcinoma|malignant)\b", text))
    normal = bool(re.search(r"\b(normal|non[- ]tumou?r|healthy control)\b", text))

    if tumour == normal:
        return None

    return "tumour" if tumour else "normal"


def verify_pair_records(
    tumour: SampleRecord,
    normal: SampleRecord,
) -> PairVerification:
    """Compare GEO records without granting researcher approval."""
    evidence = {
        "tumour_record": asdict(tumour),
        "normal_record": asdict(normal),
        "patient_id_evidence": {},
        "role_evidence": {},
    }

    if tumour.accession == normal.accession:
        status = "conflicting"
        reason = "The same GEO sample cannot form both sides of a pair."
    else:
        tumour_ids = _patient_ids(tumour)
        normal_ids = _patient_ids(normal)
        tumour_role = _sample_role(tumour)
        normal_role = _sample_role(normal)

        evidence["patient_id_evidence"] = {
            "tumour_ids": sorted(tumour_ids),
            "normal_ids": sorted(normal_ids),
        }
        evidence["role_evidence"] = {
            "tumour_role": tumour_role,
            "normal_role": normal_role,
        }

        if len(tumour_ids) > 1 or len(normal_ids) > 1:
            status = "ambiguous"
            reason = "A sample has multiple explicit patient-ID candidates."
        elif tumour_ids and normal_ids and tumour_ids.isdisjoint(normal_ids):
            status = "conflicting"
            reason = "The records identify different patients."
        elif tumour_role == "normal" or normal_role == "tumour":
            status = "conflicting"
            reason = "The sample roles contradict the proposed pair."
        elif (
            len(tumour_ids) == 1
            and tumour_ids == normal_ids
            and tumour_role == "tumour"
            and normal_role == "normal"
        ):
            status = "corroborated"
            reason = (
                "Both records report the same explicit patient ID and "
                "compatible sample roles; researcher approval is still required."
            )
        else:
            status = "ambiguous"
            reason = (
                "The records do not provide sufficient matching patient-ID "
                "and sample-role evidence."
            )

    evidence["reason"] = reason

    return PairVerification(
        tumour_accession=tumour.accession,
        normal_accession=normal.accession,
        status=status,
        approved=False,
        evidence=evidence,
    )


async def verify_geo_pair(
    tumour_accession: str,
    normal_accession: str,
    client: httpx.AsyncClient | None = None,
) -> PairVerification:
    """Fetch and verify both records; failures remain explicitly unavailable."""
    try:
        tumour, normal = await _fetch_both(
            tumour_accession, normal_accession, client
        )
        return verify_pair_records(tumour, normal)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        return PairVerification(
            tumour_accession=tumour_accession,
            normal_accession=normal_accession,
            status="unavailable",
            approved=False,
            evidence={
                "reason": "GEO sample records could not be verified.",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )


async def _fetch_both(
    tumour_accession: str,
    normal_accession: str,
    client: httpx.AsyncClient | None,
) -> tuple[SampleRecord, SampleRecord]:
    if client is not None:
        tumour = await fetch_geo_sample(tumour_accession, client)
        normal = await fetch_geo_sample(normal_accession, client)
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as session:
            tumour = await fetch_geo_sample(tumour_accession, session)
            normal = await fetch_geo_sample(normal_accession, session)

    return tumour, normal
