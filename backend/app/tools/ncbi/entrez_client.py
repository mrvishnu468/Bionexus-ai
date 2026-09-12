import os
import xml.etree.ElementTree as ET

from Bio import Entrez

from app.models.dataset import SRADataset


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

            organism = None
            sample_metadata = []

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

                if organism is None:
                    organism = sample_organism

                attributes = {}

                for attribute in sample.findall(
                    "SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE"
                ):
                    tag = attribute.findtext("TAG")
                    value = attribute.findtext("VALUE")

                    if tag and value:
                        attributes[tag] = value

                sample_metadata.append(
                    {
                        "accession": sample_accession,
                        "title": sample_title,
                        "organism": sample_organism,
                        "attributes": attributes,
                        "experiment_accession": (
                            experiment_accession
                        ),
                        "study_accession": study_accession,
                    }
                )

            study_title = None
            study_abstract = None

            study_descriptor = package.find(
                "STUDY/DESCRIPTOR"
            )

            if study_descriptor is not None:
                study_title = study_descriptor.findtext(
                    "STUDY_TITLE"
                )

                study_abstract = (
                    study_descriptor.findtext(
                        "STUDY_ABSTRACT"
                    )
                )

            sample_count = len(
                package.findall("SAMPLE")
            )

            run_count = len(
                package.findall("RUN_SET/RUN")
            )

            datasets.append(
                SRADataset(
                    accession=experiment_accession,
                    study_accession=study_accession,
                    title=experiment_title,
                    organism=organism,
                    library_strategy=library_strategy,
                    library_source=library_source,
                    description=description,
                    sample_count=sample_count,
                    run_count=run_count,
                    study_title=study_title,
                    study_abstract=study_abstract,
                    experiment_type=experiment_type,
                    samples=sample_metadata,
                )
            )

        return datasets


ncbi_client = NCBIClient()