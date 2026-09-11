import asyncio

from app.models.research import ResearchStatus
from app.services.research_store import research_store


async def run_research_workflow(research_id: str) -> None:
    stages = [
        ResearchStatus.PLANNING,
        ResearchStatus.DATASET_DISCOVERY,
        ResearchStatus.DATASET_EVALUATION,
        ResearchStatus.ANALYSIS,
        ResearchStatus.PATHWAYS,
        ResearchStatus.LITERATURE,
        ResearchStatus.SCIENTIFIC_REVIEW,
        ResearchStatus.REPORT,
        ResearchStatus.COMPLETED,
    ]

    for status in stages:
        research_store.update_status(research_id, status)
        await asyncio.sleep(2)