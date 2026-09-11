from app.models.dataset import SRADataset
from app.models.study import StudySummary


class StudyAggregator:
    def aggregate(
        self,
        study_accession: str,
        datasets: list[SRADataset],
    ) -> StudySummary:
        if not datasets:
            return StudySummary(
                accession=study_accession,
            )

        first_dataset = datasets[0]

        experiment_accessions = [
            dataset.accession
            for dataset in datasets
            if dataset.accession
        ]

        sample_count = sum(
            dataset.sample_count or 0
            for dataset in datasets
        )

        run_count = sum(
            dataset.run_count or 0
            for dataset in datasets
        )

        return StudySummary(
            accession=study_accession,
            title=first_dataset.study_title,
            abstract=first_dataset.study_abstract,
            organism=first_dataset.organism,
            experiment_count=len(experiment_accessions),
            sample_count=sample_count,
            run_count=run_count,
            experiments=experiment_accessions,
        )


study_aggregator = StudyAggregator()