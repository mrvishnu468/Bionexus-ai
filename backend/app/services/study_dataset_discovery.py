from app.models.dataset import SRAExperiment, SRADataset, SRASample
from app.models.evaluation import DatasetEvaluation
from app.services.dataset_evaluator import dataset_evaluator
from app.tools.ncbi.entrez_client import ncbi_client
from app.models.research_intent import ResearchIntent

class StudyDatasetDiscovery:
    def _collect_study(
        self,
        study_accession: str,
        page_size: int = 100,
    ) -> SRADataset | None:
        total_count, _ = ncbi_client.search_sra_study_page(
            study_accession,
            retmax=0,
        )

        if total_count == 0:
            return None

        study_datasets: list[SRADataset] = []

        for retstart in range(
            0,
            total_count,
            page_size,
        ):
            _, ids = ncbi_client.search_sra_study_page(
                study_accession,
                retmax=page_size,
                retstart=retstart,
            )

            if not ids:
                break

            records = ncbi_client.fetch_sra_records(
                ids,
            )

            datasets = ncbi_client.parse_sra_records(
                records,
            )

            for dataset in datasets:
                if dataset.study_accession == study_accession:
                    study_datasets.append(dataset)

        if not study_datasets:
            return None

        representative = study_datasets[0]

        total_samples = sum(
            dataset.sample_count or 0
            for dataset in study_datasets
        )

        total_runs = sum(
            dataset.run_count or 0
            for dataset in study_datasets
        )

        all_experiments: list[SRAExperiment] = []
        all_samples: list[SRASample] = []

        for dataset in study_datasets:
            all_experiments.extend(
                dataset.experiments,
            )
            all_samples.extend(
                dataset.samples,
            )

        return SRADataset(
            accession=study_accession,
            study_accession=study_accession,
            title=representative.study_title
            or representative.title,
            organism=representative.organism,
            library_strategy=representative.library_strategy,
            library_source=representative.library_source,
            description=representative.description,
            sample_count=total_samples,
            run_count=total_runs,
            study_title=representative.study_title,
            study_abstract=representative.study_abstract,
            experiment_type=representative.experiment_type,
            experiments=all_experiments,
            samples=all_samples,
        )
    @staticmethod
    def _build_search_query(
        query: str,
        intent: ResearchIntent | None,
    ) -> str:
        """Build an NCBI-compatible SRA query from structured intent."""
        if intent is None:
            return query.strip()

        terms: list[str] = []
        field_mappings = (
            ("disease", "All Fields"),
            ("organism", "Organism"),
            ("assay_type", "Strategy"),
        )

        for field_name, ncbi_field in field_mappings:
            field = getattr(intent, field_name, None)
            value = getattr(field, "value", None)

            if not value or not value.strip():
                continue

            if field_name == "assay_type":
                normalized = value.lower().replace("-", "").replace(" ", "")
                if normalized == "rnaseq":
                    value = "RNA-Seq"

            escaped_value = value.replace('"', "").strip()
            terms.append(f'"{escaped_value}"[{ncbi_field}]')

        return " AND ".join(terms) if terms else query.strip()


    def discover(
     self,
     query: str,
     retmax: int = 10,
    intent: ResearchIntent | None = None,
) -> list[tuple[SRADataset, DatasetEvaluation]]:
        query = query.strip()

        if not query:
            return []

        search_query = self._build_search_query(
            query,
            intent,
        )
        ids = ncbi_client.search_sra(
            search_query,
            retmax=retmax,
        )

        if not ids:
            return []

        records = ncbi_client.fetch_sra_records(
            ids,
        )

        datasets = ncbi_client.parse_sra_records(
            records,
        )

        study_accessions: list[str] = []

        for dataset in datasets:
            study_accession = dataset.study_accession

            if (
                study_accession
                and study_accession not in study_accessions
            ):
                study_accessions.append(
                    study_accession,
                )

        results: list[
            tuple[SRADataset, DatasetEvaluation]
        ] = []

        for study_accession in study_accessions:
            study = self._collect_study(
                study_accession,
            )

            if study is None:
                continue

            evaluation = dataset_evaluator.evaluate(
                study,
                intent=intent,
            )

            results.append(
                (
                    study,
                    evaluation,
                )
            )

        results.sort(
            key=lambda item: item[1].score,
            reverse=True,
        )

        return results


study_dataset_discovery = StudyDatasetDiscovery()