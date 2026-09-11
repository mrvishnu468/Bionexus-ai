from app.models.research import ResearchJob, ResearchStatus


class ResearchStore:
    def __init__(self):
        self._jobs: dict[str, ResearchJob] = {}

    def create(self, job: ResearchJob) -> ResearchJob:
        self._jobs[job.research_id] = job
        return job

    def get(self, research_id: str) -> ResearchJob | None:
        return self._jobs.get(research_id)

    def update_status(
        self,
        research_id: str,
        status: ResearchStatus,
    ) -> ResearchJob | None:
        job = self._jobs.get(research_id)

        if job is None:
            return None

        job.status = status
        return job


research_store = ResearchStore()