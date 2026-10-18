
import re

from app.models.sample_groups import (
    DetectedGroup,
    GroupDetectionResult,
    GroupDetectionStatus,
)


class SampleGroupDetector:
    GROUP_FIELDS = {
        "condition",
        "disease",
        "disease status",
        "disease_status",
        "group",
        "group name",
        "group_name",
        "phenotype",
        "status",
        "diagnosis",
        "disease state",
        "disease_state",
        "case control",
        "case_control",
    }

    TISSUE_FIELDS = {
        "tissue",
    }

    CONTROL_VALUES = {
        "control",
        "healthy",
        "normal",
        "healthy control",
        "healthy subject",
        "healthy subjects",
        "non-demented",
        "nondemented",
        "non demented",
        "unaffected",
        "unaffected control",
        "normal control",
        "normal subject",
        "normal subjects",
        "wild type",
        "wild-type",
        "wt",
    }

    DISEASE_VALUES = {
        "disease",
        "case",
        "patient",
        "patients",
        "affected",
        "alzheimer",
        "alzheimers",
        "alzheimer's disease",
        "alzheimers disease",
        "ad",
        "dementia",
        "diseased",
    }

    def _normalize(self, value: str) -> str:
        value = value.strip().lower()
        value = value.replace("_", " ")
        value = re.sub(r"\s+", " ", value)
        return value

    def _normalize_key(self, key: str) -> str:
        normalized = self._normalize(key)
        return re.sub(r"[-]+", " ", normalized)

    def _classify_value(
        self,
        value: str,
        is_tissue: bool = False,
    ) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None

        if is_tissue:
            # Remove only a trailing sample-number suffix, e.g. "_4".
            value = re.sub(r"_\d+$", "", value.strip())

            # Short coded values such as V1 do not establish a group.
            if re.fullmatch(r"[A-Za-z]{1,3}\d+", value.strip()):
                return None

        normalized = self._normalize(value)

        if normalized in self.CONTROL_VALUES:
            return "Control"

        if normalized in self.DISEASE_VALUES:
            return "Disease"

        return normalized or None

    def detect(
        self,
        samples: list[dict],
    ) -> GroupDetectionResult:
        grouped_samples: dict[str, list[str]] = {}
        evidence: dict[str, list[str]] = {}
        warnings: list[str] = []

        group_fields = {
            self._normalize_key(field)
            for field in self.GROUP_FIELDS
        }
        tissue_fields = {
            self._normalize_key(field)
            for field in self.TISSUE_FIELDS
        }

        for sample in samples:
            sample_accession = sample.get("accession", "")
            attributes = sample.get("attributes", {})

            if not isinstance(attributes, dict):
                attributes = {}

            matched_group = None
            matched_evidence = None

            for key, value in attributes.items():
                normalized_key = self._normalize_key(key)
                is_tissue = normalized_key in tissue_fields

                if (
                    normalized_key not in group_fields
                    and not is_tissue
                ):
                    continue

                group = self._classify_value(
                    value,
                    is_tissue=is_tissue,
                )

                if group is not None:
                    matched_group = group
                    matched_evidence = f"{key}={value}"
                    break

            if matched_group is None:
                warnings.append(
                    f"No explicit experimental group found for "
                    f"sample {sample_accession}."
                )
                continue

            grouped_samples.setdefault(
                matched_group,
                [],
            ).append(sample_accession)

            evidence.setdefault(
                matched_group,
                [],
            ).append(matched_evidence)

        groups = [
            DetectedGroup(
                name=name,
                sample_accessions=accessions,
                evidence=evidence[name],
                confidence=(
                    1.0
                    if name in {"Control", "Disease"}
                    else 0.8
                ),
            )
            for name, accessions in grouped_samples.items()
        ]

        if any(
            name not in {"Control", "Disease"}
            for name in grouped_samples
        ):
            warnings.append(
                "Named experimental groups were preserved from metadata; "
                "their biological roles and suitability for comparison "
                "require researcher review."
            )

        if len(groups) >= 2:
            status = GroupDetectionStatus.CONFIRMED

        elif len(groups) == 1:
            status = GroupDetectionStatus.CANDIDATE
            warnings.append(
                "Only one experimental group was explicitly detected."
            )

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
