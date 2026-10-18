
import re

from app.models.research_intent import (
    IntentField,
    IntentFieldStatus,
    IntentReviewStatus,
    ResearchIntent,
)


class ResearchIntentParser:
    """Extract clearly stated research criteria without confirming them."""

    DISEASE_TERMS = (
        "breast cancer",
        "triple-negative breast cancer",
        "tnbc",
        "lung cancer",
        "colorectal cancer",
        "prostate cancer",
        "alzheimer disease",
        "alzheimer's disease",
        "parkinson disease",
        "parkinson's disease",
        "diabetes",
    )

    ORGANISMS = {
        "homo sapiens": "Homo sapiens",
        "human": "Homo sapiens",
        "mus musculus": "Mus musculus",
        "mouse": "Mus musculus",
        "rattus norvegicus": "Rattus norvegicus",
        "rat": "Rattus norvegicus",
    }

    TISSUES = (
    "breast tissue",
    "lung tissue",
    "brain tissue",
    "liver tissue",
    "colon tissue",
    "tumor tissue",
    "tumour tissue",
    "peripheral blood",
    "whole blood",
    "blood",
)



    ASSAYS = (
        ("single-nucleus RNA-seq", "single_nucleus_rna_seq"),
        ("single nucleus RNA-seq", "single_nucleus_rna_seq"),
        ("single-cell RNA-seq", "single_cell_rna_seq"),
        ("single cell RNA-seq", "single_cell_rna_seq"),
        ("bulk RNA-seq", "bulk_rna_seq"),
        ("RNA-seq", "RNA-Seq"),
        ("RNA seq", "RNA-Seq"),
        ("RNA sequencing", "RNA-Seq"),
        ("microarray", "microarray"),
    )

    @staticmethod
    def _contains_phrase(text: str, phrase: str) -> bool:
        pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    @classmethod
    def _extract_term(
        cls,
        text: str,
        terms: tuple[str, ...],
    ) -> IntentField:
        matches = [
            term for term in terms
            if cls._contains_phrase(text, term)
        ]

        if not matches:
            return IntentField()

        # Prefer the longest match so "breast cancer" is not
        # overshadowed by a shorter, less specific term.
        longest_length = max(map(len, matches))
        longest = [
            term for term in matches
            if len(term) == longest_length
        ]

        if len(longest) > 1:
            return IntentField(
                status=IntentFieldStatus.AMBIGUOUS,
                evidence=[
                    f"Multiple candidate terms were found: {', '.join(longest)}."
                ],
            )

        term = longest[0]
        return IntentField(
            value=term,
            status=IntentFieldStatus.EXPLICIT,
            evidence=[f"Matched search phrase: '{term}'."],
        )

    @classmethod
    def _extract_organism(cls, text: str) -> IntentField:
        matches = {
            canonical
            for phrase, canonical in cls.ORGANISMS.items()
            if cls._contains_phrase(text, phrase)
        }

        if not matches:
            return IntentField()

        if len(matches) > 1:
            return IntentField(
                status=IntentFieldStatus.AMBIGUOUS,
                evidence=[
                    "The query mentions multiple possible organisms."
                ],
            )

        organism = next(iter(matches))
        return IntentField(
            value=organism,
            status=IntentFieldStatus.EXPLICIT,
            evidence=[
                f"The query explicitly identifies {organism}."
            ],
        )

    @classmethod
    def _extract_assay(cls, text: str) -> IntentField:
        matches = [
            (phrase, value)
            for phrase, value in cls.ASSAYS
            if cls._contains_phrase(text, phrase)
        ]

        if not matches:
            return IntentField()

        longest_length = max(len(phrase) for phrase, _ in matches)
        longest = [
            item for item in matches
            if len(item[0]) == longest_length
        ]
        distinct_values = {value for _, value in longest}

        if len(distinct_values) > 1:
            return IntentField(
                status=IntentFieldStatus.AMBIGUOUS,
                evidence=[
                    "The query contains conflicting assay terms."
                ],
            )

        phrase, value = longest[0]
        return IntentField(
            value=value,
            status=IntentFieldStatus.EXPLICIT,
            evidence=[f"Matched assay phrase: '{phrase}'."],
        )
    @staticmethod
    def _extract_comparison(text: str) -> IntentField:
        """Extract explicitly stated comparison groups."""
        pattern = (
            r"\b(?:compare|comparing|comparison of)\s+"
            r"(?P<left>.+?)\s+"
            r"(?:with|to|against|versus|vs\.?)\s+"
            r"(?P<right>.+?)"
            r"(?=\s+(?:for|in|from|using|across|among|within)\b"
            r"|[.,;!?]|$)"
        )

        match = re.search(pattern, text, flags=re.IGNORECASE)

        if not match:
            return IntentField()

        left = match.group("left").strip()
        right = match.group("right").strip()

        if not left or not right:
            return IntentField()

        return IntentField(
            value=f"{left} vs {right}",
            status=IntentFieldStatus.EXPLICIT,
            evidence=[
                f"Extracted comparison from query: '{match.group(0).strip()}'."
            ],
        )
    def parse(self, query: str) -> ResearchIntent:
        """Create a proposed intent; never mark it researcher-confirmed."""
        question = query.strip()

        intent = ResearchIntent(
            original_question=question,
            review_status=IntentReviewStatus.PROPOSED,
            research_goal=IntentField(
                value="Dataset discovery",
                status=IntentFieldStatus.INFERRED,
                evidence=[
                    "The query was submitted through dataset discovery."
                ],
            ),
        )

        intent.disease = self._extract_term(
            question,
            self.DISEASE_TERMS,
        )
        intent.organism = self._extract_organism(question)
        intent.tissue = self._extract_term(
            question,
            self.TISSUES,
        )
        intent.assay_type = self._extract_assay(question)
        intent.comparison = self._extract_comparison(question)
        return intent


research_intent_parser = ResearchIntentParser()
