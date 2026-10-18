
from __future__ import annotations

import gzip
import io
import re
from collections import defaultdict
from typing import Any

from app.services.geo_expression_service import (
    GeoRetrievalError,
    GeoSeriesMatrix,
)
from app.services.sample_group_detector import sample_group_detector


_TABLE_BEGIN = "!series_matrix_table_begin"

_PATIENT_FIELD_PATTERN = re.compile(
    r"(?:patient|subject|donor|individual)"
    r"[\s_-]*(?:id|identifier|number|no\.?)\b",
    re.IGNORECASE,
)

# These identifiers are candidates, not verified patient identities.
_PATIENT_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:GT|PATIENT|PAT|SUBJECT|SUBJ|DONOR|CASE)[-_ ]?\d+(?![A-Za-z0-9])",
    re.IGNORECASE,
)

_TUMOUR_PATTERN = re.compile(
    r"\b(?:tumou?r|cancer[\s_-]+tissue|malignant[\s_-]+tissue)(?![A-Za-z])",
    re.IGNORECASE,
)

_NORMAL_PATTERN = re.compile(
    r"\b(?:normal|non[- ]tumou?r|adjacent normal)\b",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    """Clean a quoted value from a GEO metadata row."""
    return value.strip().strip('"').strip()


def _metadata_values(line: str) -> list[str]:
    """Parse values from a tab-separated GEO metadata row."""
    fields = line.rstrip("\r\n").split("\t")
    return [_clean(value) for value in fields[1:]]


def _extract_patient_id(
    title: str,
    characteristics: dict[str, str],
) -> tuple[str | None, str | None]:
    """Return a tentative patient ID and its provenance."""
    for key, value in characteristics.items():
        if _PATIENT_FIELD_PATTERN.search(key) and value.strip():
            return (
                value.strip(),
                f"Explicit metadata: {key}={value}",
            )

    match = _PATIENT_TOKEN_PATTERN.search(title)
    if match:
        return (
            match.group(0).strip(),
            f"Candidate extracted from sample title: {title}",
        )

    return None, None


def _read_sample_metadata(
    matrix: GeoSeriesMatrix,
) -> dict[str, Any]:
    """Read GEO sample metadata without loading the expression table."""
    try:
        with gzip.GzipFile(
            fileobj=io.BytesIO(matrix.payload),
            mode="rb",
        ) as compressed:
            with io.TextIOWrapper(
                compressed,
                encoding="utf-8",
                errors="strict",
            ) as text_stream:
                accessions: list[str] = []
                titles: list[str] = []
                sources: list[str] = []
                characteristics_by_sample: list[dict[str, str]] = []

                for line in text_stream:
                    if line.startswith(_TABLE_BEGIN):
                        break

                    if line.startswith("!Sample_geo_accession"):
                        accessions = _metadata_values(line)

                    elif line.startswith("!Sample_title"):
                        titles = _metadata_values(line)

                    elif line.startswith("!Sample_source_name_ch1"):
                        sources = _metadata_values(line)

                    elif line.startswith("!Sample_characteristics_ch1"):
                        values = _metadata_values(line)

                        if not characteristics_by_sample:
                            characteristics_by_sample = [
                                {} for _ in values
                            ]

                        if len(values) != len(characteristics_by_sample):
                            raise GeoRetrievalError(
                                "GEO sample characteristics do not align "
                                "with sample metadata."
                            )

                        for index, raw_value in enumerate(values):
                            if ":" not in raw_value:
                                continue

                            key, value = raw_value.split(":", 1)
                            key = key.strip()
                            value = value.strip()

                            if key and value:
                                characteristics_by_sample[index][key] = value

    except GeoRetrievalError:
        raise
    except (OSError, EOFError, UnicodeError) as exc:
        raise GeoRetrievalError(
            "Unable to read GEO sample metadata from the retrieved matrix."
        ) from exc

    sample_count = len(accessions)

    if sample_count == 0:
        raise GeoRetrievalError(
            "The GEO matrix does not contain sample accessions."
        )

    if len(set(accessions)) != sample_count:
        raise GeoRetrievalError(
            "The GEO matrix contains duplicate sample accessions."
        )

    if len(titles) != sample_count:
        raise GeoRetrievalError(
            "GEO sample titles do not align with sample accessions."
        )

    # Source names are optional, but if present they must align.
    if not sources:
        sources = [""] * sample_count
    elif len(sources) != sample_count:
        raise GeoRetrievalError(
            "GEO source names do not align with sample accessions."
        )

    if not characteristics_by_sample:
        characteristics_by_sample = [{} for _ in accessions]
    elif len(characteristics_by_sample) != sample_count:
        raise GeoRetrievalError(
            "GEO sample characteristics do not align "
            "with sample accessions."
        )

    return {
        "accessions": accessions,
        "titles": titles,
        "sources": sources,
        "characteristics_by_sample": characteristics_by_sample,
    }


def _find_pairing_candidates(
    samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Identify tentative Tumour/Normal pairs using patient-ID candidates.

    Sample titles can suggest biological roles, but cannot independently
    establish patient identity. Returned pairs always require review.
    """

    def role_from_evidence(sample: dict[str, Any]) -> str | None:
        title = str(sample.get("title") or "")
        inferred_group = str(sample.get("inferred_group") or "")
        group_evidence = sample.get("group_evidence") or []

        if isinstance(group_evidence, str):
            group_evidence = [group_evidence]

        evidence_text = " ".join(
            str(item) for item in group_evidence
        )
        text = f"{title} {inferred_group} {evidence_text}"

        has_tumour = bool(_TUMOUR_PATTERN.search(text))
        has_normal = bool(_NORMAL_PATTERN.search(text))

        # Conflicting or absent role evidence must not create a candidate.
        if has_tumour and not has_normal:
            return "tumour"

        if has_normal and not has_tumour:
            return "normal"

        return None

    patients: dict[
        str, dict[str, list[dict[str, Any]]]
    ] = defaultdict(
        lambda: {"tumour": [], "normal": []}
    )

    for sample in samples:
        # IMPORTANT: use the key actually created by the manifest builder.
        patient_id = sample.get("patient_id_candidate")

        if patient_id is None or not str(patient_id).strip():
            continue

        role = role_from_evidence(sample)

        if role is not None:
            patients[str(patient_id).strip()][role].append(sample)

    candidates: list[dict[str, Any]] = []

    for patient_id, roles in patients.items():
        # Multiple samples of either role make this mapping ambiguous.
        if len(roles["tumour"]) != 1 or len(roles["normal"]) != 1:
            continue

        tumour = roles["tumour"][0]
        normal = roles["normal"][0]

        candidates.append(
            {
                "patient_id_candidate": patient_id,
                "tumour_accession": tumour["accession"],
                "normal_accession": normal["accession"],
                "status": "requires_researcher_confirmation",
                "approved": False,
                "evidence": {
                    "tumour_title": tumour.get("title", ""),
                    "normal_title": normal.get("title", ""),
                    "patient_id_evidence": [
                        tumour.get("patient_id_evidence"),
                        normal.get("patient_id_evidence"),
                    ],
                },
            }
        )

    return candidates


def build_geo_sample_manifest(
    matrix: GeoSeriesMatrix,
) -> dict[str, Any]:
    """Build a structured GEO manifest with provenance and uncertainty."""
    metadata = _read_sample_metadata(matrix)

    accessions = metadata["accessions"]
    titles = metadata["titles"]
    sources = metadata["sources"]
    characteristics_by_sample = metadata[
        "characteristics_by_sample"
    ]

    samples: list[dict[str, Any]] = []
    detector_samples: list[dict[str, Any]] = []

    for index, accession in enumerate(accessions):
        characteristics = characteristics_by_sample[index]
        title = titles[index]
        source = sources[index]

        patient_id, patient_evidence = _extract_patient_id(
            title,
            characteristics,
        )

        attributes = dict(characteristics)
        attributes["sample_title"] = title

        if source:
            attributes["source_name"] = source

        detector_samples.append(
            {
                "accession": accession,
                "attributes": attributes,
            }
        )

        samples.append(
            {
                "accession": accession,
                "title": title,
                "source_name": source or None,
                "characteristics": characteristics,
                "inferred_group": None,
                "group_evidence": [],
                "patient_id_candidate": patient_id,
                "patient_id_evidence": patient_evidence,
            }
        )

    detection = sample_group_detector.detect(detector_samples)

    group_by_accession: dict[str, str] = {}
    evidence_by_accession: dict[str, list[str]] = {}

    for group in detection.groups:
        for index, accession in enumerate(group.sample_accessions):
            group_by_accession[accession] = group.name

            if index < len(group.evidence):
                evidence_by_accession.setdefault(
                    accession, []
                ).append(group.evidence[index])

    for sample in samples:
        accession = sample["accession"]
        sample["inferred_group"] = group_by_accession.get(accession)
        sample["group_evidence"] = evidence_by_accession.get(
            accession, []
        )

    pairing_candidates = _find_pairing_candidates(samples)
    warnings = list(detection.warnings)

    if any(sample["patient_id_candidate"] for sample in samples):
        warnings.append(
            "Patient identifiers are unverified candidates. "
            "Review their provenance before accepting any pairing."
        )

    if not pairing_candidates:
        warnings.append(
            "No explicit Tumour/Normal patient pairs were identified; "
            "this does not prove samples are unpaired."
        )

    if any(
        sample["patient_id_evidence"]
        and sample["patient_id_evidence"].startswith(
            "Candidate extracted from sample title:"
        )
        for sample in samples
    ):
        warnings.append(
            "Some patient identifiers were inferred from sample titles "
            "using a conservative pattern and require researcher review."
        )

    return {
        "accession": matrix.accession,
        "samples": samples,
        "sample_count": len(samples),
        "detected_groups": [
            {
                "name": group.name,
                "sample_accessions": group.sample_accessions,
                "evidence": group.evidence,
                "confidence": group.confidence,
            }
            for group in detection.groups
        ],
        "group_detection_status": detection.status,
        "pairing_candidates": pairing_candidates,
        "pairing_approved": False,
        "warnings": list(dict.fromkeys(warnings)),
    }
