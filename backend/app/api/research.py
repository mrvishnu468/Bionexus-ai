import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.research import ResearchJob, ResearchStatus
from app.services.research_store import research_store
from app.services.research_workflow import run_research_workflow


router = APIRouter(prefix="/api/research", tags=["Research"])


class ResearchRequest(BaseModel):
    question: str


class ResearchStatusUpdate(BaseModel):
    status: ResearchStatus


@router.post("", response_model=ResearchJob)
async def start_research(request: ResearchRequest):
    research_id = str(uuid4())

    research_job = ResearchJob(
        research_id=research_id,
        question=request.question,
        status=ResearchStatus.QUEUED,
    )

    research_store.create(research_job)

    asyncio.create_task(run_research_workflow(research_id))

    return research_job


@router.get("/{research_id}", response_model=ResearchJob)
async def get_research(research_id: str):
    research_job = research_store.get(research_id)

    if research_job is None:
        raise HTTPException(
            status_code=404,
            detail="Research job not found.",
        )

    return research_job


@router.patch("/{research_id}/status", response_model=ResearchJob)
async def update_research_status(
    research_id: str,
    request: ResearchStatusUpdate,
):
    research_job = research_store.update_status(
        research_id,
        request.status,
    )

    if research_job is None:
        raise HTTPException(
            status_code=404,
            detail="Research job not found.",
        )

    return research_job