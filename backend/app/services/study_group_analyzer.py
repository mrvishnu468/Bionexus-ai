from app.models.sample_groups import GroupDetectionResult
from app.services.sample_group_detector import sample_group_detector
from app.services.study_sample_collector import study_sample_collector


class StudyGroupAnalyzer:
    def analyze(
        self,
        study_accession: str,
        page_size: int = 100,
        retmax: int | None = None,
    ) -> GroupDetectionResult:
        if retmax is not None:
            page_size = retmax

        samples = study_sample_collector.collect(
            study_accession,
            page_size=page_size,
        )

        if not samples:
            return sample_group_detector.detect([])

        return sample_group_detector.detect(samples)


study_group_analyzer = StudyGroupAnalyzer()