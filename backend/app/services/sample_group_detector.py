import re

from app.models.sample_groups import (
    DetectedGroup,
    GroupDetectionResult,
    GroupDetectionStatus,
)


class SampleGroupDetector:
    GROUP_FIELDS = {
        "condition", "disease", "disease status", "disease_status",
        "group", "group name", "group_name", "phenotype", "status",
        "diagnosis", "disease state", "disease_state",
        "case control", "case_control",
    }
    TISSUE_FIELDS = {"tissue"}
    TITLE_FIELDS = {"sample title", "title", "sample_name"}
    SOURCE_FIELDS = {"source name", "source_name"}

    CONTROL_VALUES = {
        "control", "healthy", "normal", "healthy control",
        "healthy subject", "healthy subjects", "non-demented",
        "nondemented", "non demented", "unaffected",
        "unaffected control", "normal control", "normal subject",
        "normal subjects", "wild type", "wild-type", "wt",
    }
    DISEASE_VALUES = {
        "disease", "case", "patient", "patients", "affected",
        "alzheimer", "alzheimers", "alzheimer's disease",
        "alzheimers disease", "ad", "dementia", "diseased",
    }

    _TUMOUR_PATTERN = re.compile(
        r"\b(?:tumou?r|carcinoma|adenocarcinoma|malignant)\b",
        re.IGNORECASE,
    )
    _NORMAL_PATTERN = re.compile(
        r"\b(?:normal|healthy|non[- ]tumou?r|"
        r"adjacent normal|non[- ]malignant)\b",
        re.IGNORECASE,
    )

    def _normalize(self, value: str) -> str:
        value = value.strip().lower().replace("_", " ")
        return re.sub(r"\s+", " ", value)

    def _normalize_key(self, key: str) -> str:
        return re.sub(r"[-]+", " ", self._normalize(key))

    def _classify_value(
        self,
        value: str,
        is_tissue: bool = False,
    ) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None

        if is_tissue:
            value = re.sub(r"_\d+$", "", value.strip())
            if re.fullmatch(r"[A-Za-z]{1,3}\d+", value):
                return None

        normalized = self._normalize(value)

        if normalized in self.CONTROL_VALUES:
            return "Control"
        if normalized in self.DISEASE_VALUES:
            return "Disease"

        return normalized or None

    def _classify_sample_text(self, value: str) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None

        tumour = bool(self._TUMOUR_PATTERN.search(value))
        normal = bool(self._NORMAL_PATTERN.search(value))

        # Do not infer a group when the text is ambiguous.
        if tumour == normal:
            return None

        return "Tumour" if tumour else "Normal"

    def detect(self, samples: list[dict]) -> GroupDetectionResult:
        grouped_samples: dict[str, list[str]] = {}
        evidence: dict[str, list[str]] = {}
        warnings: list[str] = []

        group_fields = {
            self._normalize_key(field) for field in self.GROUP_FIELDS
        }
        tissue_fields = {
            self._normalize_key(field) for field in self.TISSUE_FIELDS
        }
        title_fields = {
            self._normalize_key(field) for field in self.TITLE_FIELDS
        }
        source_fields = {
            self._normalize_key(field) for field in self.SOURCE_FIELDS
        }

        for sample in samples:
            accession = sample.get("accession", "")
            attributes = sample.get("attributes", {})
            if not isinstance(attributes, dict):
                attributes = {}

            matched_group = None
            matched_evidence = None

            # Prefer explicit structured group characteristics.
            for key, value in attributes.items():
                normalized_key = self._normalize_key(key)
                if (
                    normalized_key not in group_fields
                    and normalized_key not in tissue_fields
                ):
                    continue

                group = self._classify_value(
                    value,
                    is_tissue=normalized_key in tissue_fields,
                )
                if group is not None:
                    matched_group = group
                    matched_evidence = f"{key}={value}"
                    break

            # Fall back to explicit sample titles and source descriptions.
            if matched_group is None:
                for key, value in attributes.items():
                    normalized_key = self._normalize_key(key)
                    if (
                        normalized_key not in title_fields
                        and normalized_key not in source_fields
                    ):
                        continue

                    group = self._classify_sample_text(value)
                    if group is not None:
                        matched_group = group
                        matched_evidence = f"{key}={value}"
                        break

            if matched_group is None:
                warnings.append(
                    f"No unambiguous experimental group found for "
                    f"sample {accession}."
                )
                continue

            grouped_samples.setdefault(matched_group, []).append(accession)
            evidence.setdefault(matched_group, []).append(matched_evidence)

        groups = [
            DetectedGroup(
                name=name,
                sample_accessions=accessions,
                evidence=evidence[name],
                confidence=1.0 if name in {"Control", "Disease"} else 0.8,
            )
            for name, accessions in grouped_samples.items()
        ]

        if any(name not in {"Control", "Disease"} for name in grouped_samples):
            warnings.append(
                "Metadata-derived group labels are tentative; "
                "researcher review is required."
            )

        if len(groups) >= 2:
            status = GroupDetectionStatus.CONFIRMED
        elif len(groups) == 1:
            status = GroupDetectionStatus.CANDIDATE
            warnings.append("Only one experimental group was detected.")
        else:
            status = GroupDetectionStatus.UNKNOWN
            warnings.append(
                "Experimental groups could not be determined "
                "from sample metadata."
            )

        return GroupDetectionResult(
            status=status,
            groups=groups,
            warnings=warnings,
        )


sample_group_detector = SampleGroupDetector()