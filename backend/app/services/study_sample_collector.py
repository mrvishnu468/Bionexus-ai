from app.tools.ncbi.entrez_client import ncbi_client


class StudySampleCollector:
    def collect(
        self,
        study_accession: str,
        page_size: int = 100,
        retmax: int | None = None,
    ) -> list[dict]:
        if retmax is not None:
            page_size = retmax

        total_count, _ = ncbi_client.search_sra_study_page(
            study_accession,
            retmax=0,
        )

        if total_count == 0:
            return []

        samples: list[dict] = []

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

            records = ncbi_client.fetch_sra_records(ids)
            datasets = ncbi_client.parse_sra_records(records)

            for dataset in datasets:
                if dataset.study_accession != study_accession:
                    continue

                for sample in dataset.samples:
                    sample_data = sample.model_dump()

                    if not sample_data.get(
                        "study_accession"
                    ):
                        sample_data["study_accession"] = (
                            study_accession
                        )

                    if not sample_data.get(
                        "experiment_accession"
                    ):
                        sample_data["experiment_accession"] = (
                            dataset.accession
                        )

                    samples.append(sample_data)

        return samples


study_sample_collector = StudySampleCollector()