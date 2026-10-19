
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
        "triple-negative breast cancer",
        "triple negative breast cancer",
        "non-small cell lung cancer",
        "small cell lung cancer",
        "acute myeloid leukemia",
        "acute lymphoblastic leukemia",
        "chronic lymphocytic leukemia",
        "chronic myeloid leukemia",
        "non-hodgkin lymphoma",
        "hodgkin lymphoma",
        "systemic lupus erythematosus",
        "inflammatory bowel disease",
        "idiopathic pulmonary fibrosis",
        "chronic obstructive pulmonary disease",
        "polycystic ovary syndrome",
        "type 1 diabetes",
        "type 2 diabetes",
        "multiple sclerosis",
        "multiple myeloma",
        "hepatocellular carcinoma",
        "renal cell carcinoma",
        "colorectal carcinoma",
        "glioblastoma multiforme",
        "coronary artery disease",
        "chronic kidney disease",
        "acute kidney injury",
        "ulcerative colitis",
        "rheumatoid arthritis",
        "osteoarthritis",
        "osteoporosis",
        "endometriosis",
        "melanoma",
        "glioblastoma",
        "glioma",
        "leukemia",
        "leukaemia",
        "lymphoma",
        "myeloma",
        "ovarian cancer",
        "pancreatic cancer",
        "liver cancer",
        "gastric cancer",
        "stomach cancer",
        "esophageal cancer",
        "oesophageal cancer",
        "kidney cancer",
        "renal cancer",
        "bladder cancer",
        "thyroid cancer",
        "cervical cancer",
        "endometrial cancer",
        "uterine cancer",
        "prostate cancer",
        "colorectal cancer",
        "colon cancer",
        "rectal cancer",
        "triple-negative breast cancer",
        "breast cancer",
        "lung cancer",
        "brain cancer",
        "skin cancer",
        "alzheimer's disease",
        "alzheimer disease",
        "parkinson's disease",
        "parkinson disease",
        "huntington's disease",
        "huntington disease",
        "crohn's disease",
        "crohn disease",
        "fatty liver disease",
        "nonalcoholic fatty liver disease",
        "non-alcoholic steatohepatitis",
        "cardiovascular disease",
        "heart failure",
        "atherosclerosis",
        "pulmonary fibrosis",
        "diabetes mellitus",
        "diabetes",
        "obesity",
        "asthma",
        "copd",
        "nash",
        "nafld",
        "nsclc",
        "tnbc",
        "aml",
        "cll",
        "cml",
        "sle",
        "ibd",
        "pcos",
        "covid-19",
        "covid 19",
        "sars-cov-2 infection",
        "tuberculosis",
        "hiv infection",
        "hiv",
        "aids",
        "malaria",
        "dengue",
        "hepatitis b",
        "hepatitis c",
        "sepsis",
        "epilepsy",
        "anemia",
        "anaemia",
        "human immunodeficiency virus",
        "multiple myeloma",
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
    def _extract_disease(cls, text: str) -> IntentField:
        """Extract a specific disease or flag multiple diseases."""
        matches = list(dict.fromkeys(
            term.casefold()
            for term in cls.DISEASE_TERMS
            if cls._contains_phrase(text, term)
        ))

        if not matches:
            return IntentField()

        # Remove shorter matches contained in a more specific term.
        specific = [
            term for term in matches
            if not any(
                term != other and term in other
                for other in matches
            )
        ]

        if len(specific) > 1:
            return IntentField(
                status=IntentFieldStatus.AMBIGUOUS,
                evidence=[
                    "Multiple candidate diseases were found: "
                    + ", ".join(specific)
                ],
            )

        term = specific[0]
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

        intent.disease = self._extract_disease(question)
        intent.organism = self._extract_organism(question)
        intent.tissue = self._extract_term(
            question,
            self.TISSUES,
        )
        intent.assay_type = self._extract_assay(question)
        intent.comparison = self._extract_comparison(question)
        return intent


research_intent_parser = ResearchIntentParser()



