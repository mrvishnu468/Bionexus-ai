import os
import xml.etree.ElementTree as ET

from Bio import Entrez

from app.models.dataset import (
    SRADataset,
    SRAExperiment,
    SRASample,
    SRARun,
)


class NCBIClient:
    def __init__(self):
        self.email = os.getenv(
            "NCBI_EMAIL",
            "bionexus@example.com",
        )
        Entrez.email = self.email

    def search_sra(
        self,
        query: str,
        retmax: int = 10,
    ) -> list[str]:
        handle = Entrez.esearch(
            db="sra",
            term=query,
            retmax=retmax,
        )

        record = Entrez.read(handle)
        handle.close()

        return record["IdList"]

    def search_sra_study_page(
        self,
        study_accession: str,
        retmax: int = 100,
        retstart: int = 0,
    ) -> tuple[int, list[str]]:
        handle = Entrez.esearch(
            db="sra",
            term=f"{study_accession}[Study Accession]",
            retmax=retmax,
            retstart=retstart,
        )

        record = Entrez.read(handle)
        handle.close()

        total_count = int(record["Count"])
        ids = record["IdList"]

        return total_count, ids

    def search_sra_study(
        self,
        study_accession: str,
        retmax: int = 100,
        retstart: int = 0,
    ) -> list[str]:
        handle = Entrez.esearch(
            db="sra",
            term=f"{study_accession}[Study Accession]",
            retmax=retmax,
            retstart=retstart,
        )

        record = Entrez.read(handle)
        handle.close()

        return record["IdList"]

    def fetch_sra_records(
        self,
        ids: list[str],
    ) -> str:
        if not ids:
            return ""

        handle = Entrez.efetch(
            db="sra",
            id=",".join(ids),
            rettype="full",
            retmode="text",
        )

        records = handle.read()
        handle.close()

        if isinstance(records, bytes):
            records = records.decode("utf-8")

        return records

    def parse_sra_records(
        self,
        xml_text: str,
    ) -> list[SRADataset]:
        if not xml_text:
            return []

        root = ET.fromstring(xml_text)
        datasets = []

        for package in root.findall("EXPERIMENT_PACKAGE"):
            experiment = package.find("EXPERIMENT")

            if experiment is None:
                continue

            experiment_accession = experiment.get(
                "accession",
                "",
            )

            experiment_title = experiment.findtext(
                "TITLE"
            )

            study_ref = experiment.find("STUDY_REF")

            study_accession = (
                study_ref.get("accession")
                if study_ref is not None
                else None
            )

            design = experiment.find("DESIGN")

            description = (
                design.findtext("DESIGN_DESCRIPTION")
                if design is not None
                else None
            )

            library = experiment.find(
                "DESIGN/LIBRARY_DESCRIPTOR"
            )

            library_strategy = (
                library.findtext("LIBRARY_STRATEGY")
                if library is not None
                else None
            )

            library_source = (
                library.findtext("LIBRARY_SOURCE")
                if library is not None
                else None
            )

            experiment_type = library_source

            study_title = None
            study_abstract = None

            study_descriptor = package.find(
                "STUDY/DESCRIPTOR"
            )

            if study_descriptor is not None:
                study_title = study_descriptor.findtext(
                    "STUDY_TITLE"
                )

                study_abstract = study_descriptor.findtext(
                    "STUDY_ABSTRACT"
                )

            runs: list[SRARun] = []

            for run in package.findall("RUN_SET/RUN"):
                run_accession = run.get(
                    "accession",
                    "",
                )

                experiment_ref = run.find(
                    "EXPERIMENT_REF"
                )

                run_experiment_accession = (
                    experiment_ref.get("accession")
                    if experiment_ref is not None
                    else experiment_accession
                )

                sample_accession = None

                for member in run.findall(
                    "Pool/Member"
                ):
                    sample_ref = member.get(
                        "accession"
                    )

                    if sample_ref:
                        sample_accession = sample_ref
                        break

                runs.append(
                    SRARun(
                        accession=run_accession,
                        experiment_accession=(
                            run_experiment_accession
                        ),
                        sample_accession=sample_accession,
                    )
                )

            samples: list[SRASample] = []

            for sample in package.findall("SAMPLE"):
                sample_accession = sample.get(
                    "accession",
                    "",
                )

                sample_title = sample.findtext(
                    "TITLE"
                )

                sample_organism = sample.findtext(
                    "SAMPLE_NAME/SCIENTIFIC_NAME"
                )

                attributes: dict[str, str] = {}

                for attribute in sample.findall(
                    "SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE"
                ):
                    tag = attribute.findtext("TAG")
                    value = attribute.findtext("VALUE")

                    if tag and value:
                        attributes[tag] = value

                sample_runs = [
                    run.model_copy()
                    for run in runs
                    if run.sample_accession
                    == sample_accession
                ]

                samples.append(
                    SRASample(
                        accession=sample_accession,
                        title=sample_title,
                        organism=sample_organism,
                        attributes=attributes,
                        experiment_accession=(
                            experiment_accession
                        ),
                        study_accession=study_accession,
                        runs=sample_runs,
                    )
                )

            experiment_model = SRAExperiment(
    accession=experiment_accession,
    title=experiment_title,
    study_accession=study_accession,
    organism=(
        samples[0].organism
        if samples
        else None
    ),
    samples=samples,
)

            datasets.append(
                SRADataset(
                    accession=experiment_accession,
                    study_accession=study_accession,
                    title=experiment_title,
                    organism=(
                        samples[0].organism
                        if samples
                        else None
                    ),
                    library_strategy=library_strategy,
                    library_source=library_source,
                    description=description,
                    sample_count=len(samples),
                    run_count=len(runs),
                    study_title=study_title,
                    study_abstract=study_abstract,
                    experiment_type=experiment_type,
                    experiments=[experiment_model],
                    samples=samples,
                )
            )

        return datasets


ncbi_client = NCBIClient()