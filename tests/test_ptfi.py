import pytest
from fastapi.testclient import TestClient
import mongomock
from unittest.mock import patch
from bson import ObjectId
import os

# Import the app here, it's safe now because we use dependency overrides
from echosystem.ptfi.main import app, get_db

# --- Fixtures ---

@pytest.fixture
def mock_db():
    """Fixture to create an in-memory mongomock database instance."""
    client = mongomock.MongoClient()
    return client.db

@pytest.fixture
def client(mock_db):
    """
    Fixture to create a TestClient with the get_db dependency overridden.
    """
    # Override the dependency
    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up the override after the test
    app.dependency_overrides.clear()


# --- Sample Data for Tests ---
SAMPLE_REQUEST_ID = "test-request-ptfi-123"
SAMPLE_DOC = {
    "requestId": SAMPLE_REQUEST_ID,
    "sentiment": "neutral",
    "keywords": ["sample", "data"],
    "wordCount": 3
}

# --- Test Cases ---

def test_get_analysis_not_found(client):
    """
    Test that GET /analysis/{request_id} returns 404 for a non-existent ID.
    """
    response = client.get(f"/analysis/non-existent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis for request_id non-existent-id not found"

def test_get_analysis_success(client, mock_db):
    """
    Test that GET /analysis/{request_id} returns the correct document.
    """
    # Arrange
    inserted = mock_db.persona_analysis.insert_one(SAMPLE_DOC.copy())

    # Act
    response = client.get(f"/analysis/{SAMPLE_REQUEST_ID}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    # Check for the aliased field name in the response
    assert response_data["requestId"] == SAMPLE_REQUEST_ID
    assert response_data["sentiment"] == "neutral"
    assert response_data["_id"] == str(inserted.inserted_id)

def test_refine_analysis_not_found(client):
    """
    Test that POST /analysis/{request_id}/refine returns 404 for a non-existent ID.
    """
    # Arrange
    refinement_payload = {
        "approved_keywords": ["sample"],
        "feedback_notes": "Looks good."
    }

    # Act
    response = client.post(f"/analysis/non-existent-id/refine", json=refinement_payload)

    # Assert
    assert response.status_code == 404

def test_refine_analysis_success(client, mock_db):
    """
    Test that POST /analysis/{request_id}/refine successfully updates a document.
    """
    # Arrange
    mock_db.persona_analysis.insert_one(SAMPLE_DOC.copy())
    refinement_payload = {
        "approved_keywords": ["sample", "data"],
        "feedback_notes": "This analysis is approved."
    }

    # Act
    response = client.post(f"/analysis/{SAMPLE_REQUEST_ID}/refine", json=refinement_payload)

    # Assert response
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Assert DB state
    updated_doc = mock_db.persona_analysis.find_one({"requestId": SAMPLE_REQUEST_ID})
    assert updated_doc is not None
    assert "feedback" in updated_doc
    assert updated_doc["feedback"]["approved_keywords"] == refinement_payload["approved_keywords"]
    assert updated_doc["feedback"]["feedback_notes"] == refinement_payload["feedback_notes"]
