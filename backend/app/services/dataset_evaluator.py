
from app.models.dataset import SRADataset
from app.models.evaluation import (
    DatasetAssayType,
    DatasetEvaluation,
    DatasetSuitability,
)
from app.models.research_intent import ResearchIntent


class DatasetEvaluator:
    """Evaluate dataset relevance, analysis readiness, and suitability."""

    @staticmethod
    def _classify_assay(dataset: SRADataset) -> DatasetAssayType:
        """Classify an assay using available SRA metadata."""
        text = " ".join(
            str(value or "")
            for value in (
                getattr(dataset, "assay_type", None),
                getattr(dataset, "library_strategy", None),
                getattr(dataset, "library_source", None),
                getattr(dataset, "experiment_type", None),
                getattr(dataset, "title", None),
                getattr(dataset, "study_title", None),
                getattr(dataset, "description", None),
                getattr(dataset, "study_abstract", None),
            )
        ).upper()

        if "SINGLE NUCLEUS" in text or "SINGLE-NUCLEUS" in text:
            return DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ

        if "SINGLE CELL" in text or "SINGLE-CELL" in text:
            return DatasetAssayType.SINGLE_CELL_RNA_SEQ

        if "RNA-SEQ" in text or "RNA SEQ" in text:
            if "TRANSCRIPTOMIC" in text:
                return DatasetAssayType.BULK_RNA_SEQ
            return DatasetAssayType.OTHER

        return DatasetAssayType.UNKNOWN

    @staticmethod
    def _intent_value(intent: ResearchIntent | None, field_name: str):
        """Return a meaningful value from a structured intent field."""
        if intent is None:
            return None

        field = getattr(intent, field_name, None)
        if field is None:
            return None

        value = getattr(field, "value", field)
        if value is None:
            return None

        if isinstance(value, str) and not value.strip():
            return None

        return value

    @staticmethod
    def _dataset_text(dataset: SRADataset) -> str:
        """Build searchable text from available dataset metadata."""
        fields = (
            "study_title",
            "title",
            "description",
            "abstract",
            "study_abstract",
            "organism",
            "tissue",
            "assay_type",
            "library_strategy",
            "library_source",
            "experiment_type",
            "disease",
        )
        return " ".join(
            str(value)
            for name in fields
            if (value := getattr(dataset, name, None))
        ).lower()

    @staticmethod
    def _organism_matches(requested: str, observed: str) -> bool:
        """Compare common organism names without treating missing data as a match."""
        requested = requested.lower().strip()
        observed = observed.lower().strip()

        aliases = {
            "human": ("human", "homo sapiens"),
            "homo sapiens": ("human", "homo sapiens"),
            "mouse": ("mouse", "mus musculus"),
            "mus musculus": ("mouse", "mus musculus"),
            "rat": ("rat", "rattus norvegicus"),
            "rattus norvegicus": ("rat", "rattus norvegicus"),
        }

        requested_terms = aliases.get(requested, (requested,))
        observed_terms = aliases.get(observed, (observed,))

        return any(
            left == right or left in right or right in left
            for left in requested_terms
            for right in observed_terms
        )

    def evaluate(
        self,
        dataset: SRADataset,
        intent: ResearchIntent | None = None,
    ) -> DatasetEvaluation:
        """Return transparent relevance, readiness, and suitability scores."""
        reasons: list[str] = []
        warnings: list[str] = []
        unknowns: list[str] = []

        relevance_points = 0
        relevance_maximum = 0
        confirmed_organism_mismatch = False

        organism_intent = self._intent_value(intent, "organism")
        disease_intent = self._intent_value(intent, "disease")
        tissue_intent = self._intent_value(intent, "tissue")
        assay_intent = self._intent_value(intent, "assay_type")

        dataset_organism = getattr(dataset, "organism", None)
        dataset_text = self._dataset_text(dataset)
        assay = self._classify_assay(dataset)

        # 1. Relevance: organism
        if organism_intent:
            relevance_maximum += 25

            if dataset_organism:
                if self._organism_matches(
                    str(organism_intent), str(dataset_organism)
                ):
                    relevance_points += 25
                    reasons.append(
                        f"Organism matches the requested organism: "
                        f"{dataset_organism}."
                    )
                else:
                    confirmed_organism_mismatch = True
                    warnings.append(
                        "The dataset organism does not match the requested "
                        "organism."
                    )
            else:
                unknowns.append("Dataset organism is not reported.")
        elif dataset_organism:
            if (
                "homo sapiens" in str(dataset_organism).lower()
                or "human" in str(dataset_organism).lower()
            ):
                reasons.append("Human organism is confirmed.")
            else:
                reasons.append(
                    "Organism information is available, but no organism "
                    "preference was specified."
                )
        else:
            unknowns.append("Dataset organism is not reported.")

        # 2. Relevance: disease
        if disease_intent:
            relevance_maximum += 35
            disease_value = str(disease_intent).lower()

            if disease_value in dataset_text:
                relevance_points += 35
                reasons.append(
                    "Dataset metadata matches the requested disease."
                )
            else:
                warnings.append(
                    "The requested disease was not confirmed in the available "
                    "dataset metadata."
                )

        # 3. Relevance: tissue
        if tissue_intent:
            relevance_maximum += 20
            tissue_value = str(tissue_intent).lower()
            tissue_metadata = " ".join(
                str(getattr(dataset, name, None) or "")
                for name in (
                    "tissue",
                    "study_title",
                    "title",
                    "description",
                    "abstract",
                    "study_abstract",
                )
            ).lower()

            if tissue_value in tissue_metadata:
                relevance_points += 20
                reasons.append(
                    "Dataset metadata matches the requested tissue."
                )
            else:
                warnings.append(
                    "The requested tissue was not confirmed in the available "
                    "dataset metadata."
                )

        # 4. Relevance: assay
        if assay_intent:
            relevance_maximum += 20
            requested_assay = (
                str(assay_intent)
                .lower()
                .replace("-", "")
                .replace("_", "")
            )
            observed_assay = (
                assay.value.lower()
                .replace("-", "")
                .replace("_", "")
            )

            if (
                requested_assay in observed_assay
                or observed_assay in requested_assay
            ):
                relevance_points += 20
                reasons.append(
                    "The classified assay matches the requested assay."
                )
            elif requested_assay in dataset_text.replace(
                "-", ""
            ).replace("_", ""):
                relevance_points += 20
                reasons.append(
                    "Dataset metadata matches the requested assay."
                )
            else:
                warnings.append(
                    "The requested assay was not confirmed in the available "
                    "dataset metadata."
                )

        if relevance_maximum:
            relevance_score = round(
                100 * relevance_points / relevance_maximum
            )
        else:
            # A search without structured preferences has neutral relevance.
            relevance_score = 50

        # Preserve a modest human baseline for unfiltered discovery.
        # Do not penalize other organisms when none was requested.
        if (
            relevance_maximum == 0
            and dataset_organism
            and (
                "homo sapiens" in str(dataset_organism).lower()
                or "human" in str(dataset_organism).lower()
            )
        ):
            relevance_score = 75

        # 5. Readiness: metadata and assay evidence
        readiness_points = 0

        library_source = str(
            getattr(dataset, "library_source", None) or ""
        ).lower()

        # Include structured SRA metadata and study-level text.
        # SRA's library_strategy is especially important because RNA-Seq
        # can be reported there even when assay_type is missing.
        assay_text = " ".join(
            str(getattr(dataset, name, None) or "")
            for name in (
                "assay_type",
                "library_strategy",
                "experiment_type",
                "title",
                "study_title",
                "description",
                "abstract",
                "study_abstract",
            )
        ).lower()

        transcriptomic_confirmed = (
            "transcriptomic" in library_source
            or "transcriptomic" in assay_text
        )

        rna_seq_confirmed = (
            "rna-seq" in assay_text
            or "rna seq" in assay_text
            or "rnaseq" in assay_text
            or "rna-seq" in library_source
            or "rna seq" in library_source
            or "rnaseq" in library_source
        )

        if transcriptomic_confirmed and rna_seq_confirmed:
            readiness_points += 35
            reasons.append(
                "RNA-Seq transcriptomic evidence is available."
            )
        elif rna_seq_confirmed:
            readiness_points += 15
            warnings.append(
                "Transcriptomic library source could not be confirmed."
            )
        else:
            unknowns.append(
                "RNA-Seq transcriptomic suitability is unconfirmed."
            )

        if assay == DatasetAssayType.BULK_RNA_SEQ:
            readiness_points += 25
            reasons.append(
                "Bulk RNA-Seq is compatible with standard expression analysis."
            )
        elif assay in (
            DatasetAssayType.SINGLE_CELL_RNA_SEQ,
            DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ,
        ):
            readiness_points += 15
            warnings.append(
                "This dataset requires specialized analysis for single-cell "
                "or single-nucleus data."
            )
        elif assay == DatasetAssayType.UNKNOWN:
            warnings.append(
                "The assay type could not be confidently classified."
            )

        sample_count = getattr(dataset, "sample_count", None)
        if isinstance(sample_count, int) and sample_count >= 2:
            readiness_points += 20
            reasons.append(
                f"Dataset reports {sample_count} samples; biological group "
                "structure still needs verification."
            )
        elif isinstance(sample_count, int) and sample_count >= 0:
            unknowns.append(
                "The reported sample count does not establish adequate "
                "biological replication."
            )
        else:
            unknowns.append("Dataset sample count is not reported.")

        abstract = (
            getattr(dataset, "abstract", None)
            or getattr(dataset, "study_abstract", None)
        )
        description = getattr(dataset, "description", None)

        if abstract or description:
            readiness_points += 20
            reasons.append(
                "Study description is available for review."
            )
        else:
            unknowns.append(
                "Study abstract or description is not available."
            )

        # Run counts are technical records, not biological replicates.
        run_count = getattr(dataset, "run_count", None)
        if isinstance(run_count, int) and run_count > 0:
            reasons.append(
                f"{run_count} sequencing runs are reported; run count is not "
                "treated as biological replicate count."
            )

        readiness_score = min(readiness_points, 100)

        # 6. Suitability decision
        specialized_assay = assay in (
            DatasetAssayType.SINGLE_CELL_RNA_SEQ,
            DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ,
        )

        if confirmed_organism_mismatch:
            suitability = DatasetSuitability.NOT_RECOMMENDED
            suitability_score = 20
        elif specialized_assay:
            suitability = DatasetSuitability.CONDITIONAL
            suitability_score = 60
        elif (
            assay == DatasetAssayType.BULK_RNA_SEQ
            and readiness_score >= 75
            and relevance_score >= 50
        ):
            suitability = DatasetSuitability.RECOMMENDED
            suitability_score = 90
        elif readiness_score >= 35:
            suitability = DatasetSuitability.CONDITIONAL
            suitability_score = 60
        else:
            suitability = DatasetSuitability.NOT_RECOMMENDED
            suitability_score = 20

        # Overall score balances intent relevance with analysis readiness.
        score = round(
            0.60 * relevance_score + 0.40 * readiness_score
        )

        if confirmed_organism_mismatch:
            score = min(score, 59)

        return DatasetEvaluation(
            accession=dataset.accession,
            assay_type=assay,
            score=score,
            relevance_score=relevance_score,
            readiness_score=readiness_score,
            suitability_score=suitability_score,
            suitability=suitability,
            reasons=reasons,
            warnings=warnings,
            unknowns=unknowns,
        )


dataset_evaluator = DatasetEvaluator()
