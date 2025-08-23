import pytest
from fastapi.testclient import TestClient
import mongomock
from unittest.mock import MagicMock

# Import the app and dependency function
from echosystem.generator.main import app, get_db, get_ai_client
from echosystem.aiproxy.client import AIClient

# --- Fixtures ---

@pytest.fixture
def mock_db():
    """Fixture to create an in-memory mongomock database instance."""
    client = mongomock.MongoClient()
    return client.db

@pytest.fixture
def mock_ai_client():
    """Fixture to create a mock AIClient."""
    client = MagicMock(spec=AIClient)
    return client

@pytest.fixture
def client(mock_db, mock_ai_client):
    """
    Fixture to create a TestClient with dependencies overridden.
    """
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_ai_client] = lambda: mock_ai_client

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

# --- Sample Data ---
SAMPLE_REQUEST_ID = "test-request-gen-123"
SAMPLE_PERSONA_DOC = {
    "requestId": SAMPLE_REQUEST_ID,
    "latest_analysis": {
        "sentiment": "positive",
        "keywords": ["testing", "quality", "software"],
    }
}

# --- Test Cases ---

def test_generate_not_found(client):
    """
    Test that POST /generate/{request_id} returns 404 for a non-existent ID.
    """
    response = client.post(f"/generate/non-existent-id", json={"prompt": "test"})
    assert response.status_code == 404

def test_generate_success(client, mock_db, mock_ai_client):
    """
    Test successful text generation orchestration.
    """
    # Arrange
    # 1. Set up the mock DB
    mock_db.persona_analysis.insert_one(SAMPLE_PERSONA_DOC.copy())

    # 2. Configure the mock AI client's return value
    prompt = "the future of AI"
    mock_response_text = "This is a mock response."
    mock_ai_client.generate_response.return_value = mock_response_text

    # Act
    response = client.post(f"/generate/{SAMPLE_REQUEST_ID}", json={"prompt": prompt})

    # Assert
    # 1. Assert the API response is correct
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["request_id"] == SAMPLE_REQUEST_ID
    assert response_data["text"] == mock_response_text

    # 2. Assert that the AI client was called correctly
    mock_ai_client.generate_response.assert_called_once()
    # We can inspect the call arguments
    args, kwargs = mock_ai_client.generate_response.call_args
    assert args[0]["requestId"] == SAMPLE_REQUEST_ID # persona_doc
    assert args[1] == prompt # prompt
