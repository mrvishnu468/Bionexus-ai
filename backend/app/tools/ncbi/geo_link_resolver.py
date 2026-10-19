
"""Resolve SRA study accessions through NCBI's cross-database links."""

import re
from dataclasses import dataclass
from typing import Literal

from Bio import Entrez


@dataclass(frozen=True)
class GeoLinkResolution:
    """Result of resolving an SRA study to GEO Series records."""

    study_accession: str
    status: Literal["resolved", "not_found", "ambiguous", "invalid"]
    geo_accessions: tuple[str, ...]
    message: str


class GeoLinkResolver:
    """Use NCBI SRA-to-GEO links instead of text-only matching."""

    def __init__(self, email: str | None = None):
        self.email = email or Entrez.email or "bionexus@example.com"

    def resolve(self, study_accession: str) -> GeoLinkResolution:
        accession = study_accession.strip().upper()

        if not re.fullmatch(r"SRP\d+", accession):
            return self._result(
                accession,
                (),
                "Expected an SRA study accession such as SRP123456.",
                status="invalid",
            )

        Entrez.email = self.email

        try:
            with Entrez.esearch(
                db="sra",
                term=f"{accession}[Study Accession]",
                retmax=10000,
            ) as handle:
                search_result = Entrez.read(handle)

            sra_uids = search_result.get("IdList", [])
            if not sra_uids:
                return self._result(
                    accession,
                    (),
                    "No SRA records were found for this study.",
                )

            with Entrez.elink(
                dbfrom="sra",
                db="gds",
                id=",".join(sra_uids),
                linkname="sra_gds",
            ) as handle:
                link_sets = Entrez.read(handle)

            geo_uids = self._linked_geo_uids(link_sets)
            if not geo_uids:
                return self._result(
                    accession,
                    (),
                    "NCBI returned no direct SRA-to-GEO links.",
                )

            with Entrez.esummary(
                db="gds",
                id=",".join(geo_uids),
            ) as handle:
                summaries = Entrez.read(handle)

            candidates = self._linked_series_accessions(summaries)

        except Exception as exc:
            raise RuntimeError(
                f"Unable to resolve GEO links for {accession}: {exc}"
            ) from exc

        return self._result(accession, candidates)

    @staticmethod
    def _linked_geo_uids(link_sets) -> tuple[str, ...]:
        """Extract GEO record UIDs returned by the SRA-to-GEO link."""
        linked_ids: set[str] = set()

        for link_set in link_sets:
            if not hasattr(link_set, "get"):
                continue

            for group in link_set.get("LinkSetDb", []):
                if group.get("LinkName") != "sra_gds":
                    continue

                for link in group.get("Link", []):
                    uid = link.get("Id")
                    if uid:
                        linked_ids.add(str(uid))

        return tuple(sorted(linked_ids))

    
    @staticmethod
    def _linked_series_accessions(summaries) -> tuple[str, ...]:
        """Extract GEO Series accessions from NCBI GDS summaries."""
        candidates: set[str] = set()

        for summary in summaries:
            if not hasattr(summary, "get"):
                continue

            # NCBI summary formats may use either capitalization.
            accession = summary.get("accession") or summary.get("Accession")
            entry_type = summary.get("entryType") or summary.get("EntryType")

            if not isinstance(accession, str):
                continue

            accession = accession.strip().upper()

            # Never treat a GSM sample as a GEO Series just because its
            # summary contains a GSE field listing related series.
            if entry_type and str(entry_type).upper() != "GSE":
                continue

            if re.fullmatch(r"GSE\d+", accession):
                candidates.add(accession)

        return tuple(sorted(candidates, key=lambda item: int(item[3:])))


    @staticmethod
    def _result(
        study_accession: str,
        candidates: tuple[str, ...],
        missing_message: str = "No directly linked GEO Series was found.",
        status: Literal["resolved", "not_found", "ambiguous", "invalid"] | None = None,
    ) -> GeoLinkResolution:
        if status == "invalid":
            return GeoLinkResolution(
                study_accession=study_accession,
                status="invalid",
                geo_accessions=(),
                message=missing_message,
            )

        if len(candidates) == 1:
            return GeoLinkResolution(
                study_accession=study_accession,
                status="resolved",
                geo_accessions=candidates,
                message="One GEO Series was returned by the NCBI link lookup.",
            )

        if len(candidates) > 1:
            return GeoLinkResolution(
                study_accession=study_accession,
                status="ambiguous",
                geo_accessions=candidates,
                message="Multiple linked GEO Series require researcher review.",
            )

        return GeoLinkResolution(
            study_accession=study_accession,
            status="not_found",
            geo_accessions=(),
            message=missing_message,
        )


geo_link_resolver = GeoLinkResolver()
