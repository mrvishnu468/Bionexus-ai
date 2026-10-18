
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.dataset import SRADataset
from app.models.evaluation import (
    DatasetAssayType,
    DatasetEvaluation,
    DatasetSuitability,
)
from app.models.research_intent import ResearchIntent
from app.services.intent_approval import intent_approval_service


client = TestClient(app)


def add_approval_token(payload):
    intent = ResearchIntent.model_validate(payload["intent"])
    payload["approval_token"] = intent_approval_service.issue(intent)
    return payload


def test_empty_query_returns_no_datasets():
    response = client.post(
        "/api/datasets/search",
        json={"query": "   "},
    )

    assert response.status_code == 200
    assert response.json()["datasets"] == []


def test_ambiguous_intent_blocks_discovery():
    payload = {
        "query": "breast cancer gene expression",
        "intent": {
            "original_question": "Find relevant data",
            "review_status": "confirmed",
            "research_goal": {
                "value": "differential expression",
                "status": "confirmed",
            },
            "disease": {
                "value": "breast cancer",
                "status": "explicit",
            },
            "assay_type": {
                "value": None,
                "status": "ambiguous",
            },
        },
    }
    add_approval_token(payload)

    with patch(
        "app.api.datasets.study_dataset_discovery.discover"
    ) as discover:
        response = client.post(
            "/api/datasets/search",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["ready_for_ranking"] is False
    assert response.json()["datasets"] == []
    assert response.json()["clarification_questions"]
    discover.assert_not_called()


def test_confirmed_intent_returns_discovered_dataset():
    dataset = SRADataset(
        accession="SRP000001",
        study_accession="SRP000001",
        title="Breast cancer RNA-seq",
    )
    evaluation = DatasetEvaluation(
        accession="SRP000001",
        suitability=DatasetSuitability.RECOMMENDED,
        assay_type=DatasetAssayType.BULK_RNA_SEQ,
        score=90,
    )
    payload = {
        "query": "breast cancer RNA-seq",
        "intent": {
            "original_question": "Find breast cancer RNA-seq datasets",
            "review_status": "confirmed",
            "research_goal": {
                "value": "differential expression",
                "status": "confirmed",
            },
            "disease": {
                "value": "breast cancer",
                "status": "explicit",
            },
            "assay_type": {
                "value": "bulk RNA-seq",
                "status": "confirmed",
            },
        },
    }
    add_approval_token(payload)

    with patch(
        "app.api.datasets.study_dataset_discovery.discover",
        return_value=[(dataset, evaluation)],
    ) as discover:
        response = client.post(
            "/api/datasets/search",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["ready_for_ranking"] is True
    assert len(response.json()["datasets"]) == 1
    assert response.json()["datasets"][0]["dataset"]["accession"] == "SRP000001"
    discover.assert_called_once()
    assert discover.call_args.kwargs["intent"] is not None
