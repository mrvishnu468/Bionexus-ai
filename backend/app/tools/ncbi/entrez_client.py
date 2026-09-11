import os
import xml.etree.ElementTree as ET

from Bio import Entrez

from app.models.dataset import SRADataset


class NCBIClient:
    def __init__(self):
        self.email = os.getenv("NCBI_EMAIL", "bionexus@example.com")
        Entrez.email = self.email

    def search_sra(self, query: str, retmax: int = 10) -> list[str]:
        handle = Entrez.esearch(
            db="sra",
            term=query,
            retmax=retmax,
        )

        record = Entrez.read(handle)
        handle.close()

        return record["IdList"]

    def fetch_sra_records(self, ids: list[str]) -> str:
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

    def parse_sra_records(self, xml_text: str) -> list[SRADataset]:
        if not xml_text:
            return []

        root = ET.fromstring(xml_text)
        datasets = []

        for package in root.findall("EXPERIMENT_PACKAGE"):
            experiment = package.find("EXPERIMENT")

            if experiment is None:
                continue

            accession = experiment.get("accession", "")
            title = experiment.findtext("TITLE")

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

            library = experiment.find("DESIGN/LIBRARY_DESCRIPTOR")

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

            organism = None
            sample = package.find("SAMPLE")

            if sample is not None:
                organism = sample.findtext(
                    "SAMPLE_NAME/SCIENTIFIC_NAME"
                )

            datasets.append(
                SRADataset(
                    accession=accession,
                    study_accession=study_accession,
                    title=title,
                    organism=organism,
                    library_strategy=library_strategy,
                    library_source=library_source,
                    description=description,
                )
            )

        return datasets


ncbi_client = NCBIClient()