from app.models.dataset import SRADataset
from app.models.evaluation import (
    DatasetAssayType,
    DatasetEvaluation,
    DatasetSuitability,
)


class DatasetEvaluator:
    def _classify_assay(
        self,
        dataset: SRADataset,
    ) -> DatasetAssayType:
        source = (dataset.library_source or "").upper()
        experiment_type = (dataset.experiment_type or "").upper()
        combined = f"{source} {experiment_type}"

        if "SINGLE NUCLEUS" in combined:
            return DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ

        if "SINGLE CELL" in combined:
            return DatasetAssayType.SINGLE_CELL_RNA_SEQ

        if (
            dataset.library_strategy == "RNA-Seq"
            and "TRANSCRIPTOMIC" in combined
        ):
            return DatasetAssayType.BULK_RNA_SEQ

        if dataset.library_strategy == "RNA-Seq":
            return DatasetAssayType.OTHER

        return DatasetAssayType.UNKNOWN

    def evaluate(
        self,
        dataset: SRADataset,
    ) -> DatasetEvaluation:
        score = 0
        reasons: list[str] = []
        warnings: list[str] = []

        assay_type = self._classify_assay(dataset)

        if dataset.organism == "Homo sapiens":
            score += 25
            reasons.append("Human dataset.")
        elif dataset.organism:
            warnings.append(
                f"Non-human organism: {dataset.organism}."
            )
        else:
            warnings.append("Organism information is missing.")

        if dataset.library_strategy == "RNA-Seq":
            score += 25
            reasons.append("RNA-Seq data is available.")
        else:
            warnings.append(
                "Dataset is not identified as RNA-Seq."
            )

        source = (dataset.library_source or "").upper()

        if assay_type in {
            DatasetAssayType.SINGLE_CELL_RNA_SEQ,
            DatasetAssayType.SINGLE_NUCLEUS_RNA_SEQ,
        }:
            score += 10
            warnings.append(
                "Single-cell or single-nucleus data may require "
                "specialized analysis."
            )
        elif "TRANSCRIPTOMIC" in source:
            score += 20
            reasons.append("Transcriptomic data is available.")
        else:
            warnings.append(
                "Transcriptomic library source could not be confirmed."
            )

        if dataset.sample_count and dataset.sample_count >= 2:
            score += 15
            reasons.append(
                f"{dataset.sample_count} sample record(s) detected."
            )
        else:
            warnings.append(
                "Fewer than two sample records were detected."
            )

        if dataset.run_count and dataset.run_count >= 1:
            score += 10
            reasons.append(
                f"{dataset.run_count} sequencing run(s) detected."
            )
        else:
            warnings.append(
                "No sequencing runs were detected."
            )

        if dataset.study_abstract:
            score += 5
            reasons.append("Study abstract is available.")
        else:
            warnings.append("Study abstract is missing.")

        if (
            score >= 80
            and assay_type == DatasetAssayType.BULK_RNA_SEQ
        ):
            suitability = DatasetSuitability.RECOMMENDED
        elif score >= 40:
            suitability = DatasetSuitability.CONDITIONAL
        else:
            suitability = DatasetSuitability.NOT_RECOMMENDED

        return DatasetEvaluation(
            accession=dataset.accession,
            suitability=suitability,
            assay_type=assay_type,
            score=score,
            reasons=reasons,
            warnings=warnings,
        )


dataset_evaluator = DatasetEvaluator()