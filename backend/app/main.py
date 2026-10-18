from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.evaluation import router as evaluation_router
from app.api.datasets import router as datasets_router
from app.api.research import router as research_router
from app.api.intent import router as intent_router
from app.api.study_design import router as study_design_router
from app.api.geo import router as geo_router




app = FastAPI(title="BioNexus AI API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(research_router)
app.include_router(intent_router)
app.include_router(geo_router)
app.include_router(study_design_router)
app.include_router(datasets_router)
app.include_router(evaluation_router)
@app.get("/health")
async def health():
    return {"status": "ok"}