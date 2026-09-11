from app.models.dataset import SRADataset
from app.models.evaluation import DatasetEvaluation, DatasetSuitability


class DatasetEvaluator:
    def evaluate(self, dataset: SRADataset) -> DatasetEvaluation:
        score = 0
        reasons: list[str] = []
        warnings: list[str] = []

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
            warnings.append("Dataset is not identified as RNA-Seq.")

        source = (dataset.library_source or "").upper()

        if "SINGLE CELL" in source or "SINGLE NUCLEUS" in source:
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

        if score >= 80 and not any(
            "specialized analysis" in warning
            for warning in warnings
        ):
            suitability = DatasetSuitability.RECOMMENDED

        elif score >= 40:
            suitability = DatasetSuitability.CONDITIONAL

        else:
            suitability = DatasetSuitability.NOT_RECOMMENDED

        return DatasetEvaluation(
            accession=dataset.accession,
            suitability=suitability,
            score=score,
            reasons=reasons,
            warnings=warnings,
        )


dataset_evaluator = DatasetEvaluator()