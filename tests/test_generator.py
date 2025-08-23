import pytest
from fastapi.testclient import TestClient
import mongomock

# Import the app and dependency function
from echosystem.generator.main import app, get_db

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
    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

# --- Sample Data ---
SAMPLE_REQUEST_ID = "test-request-gen-123"
SAMPLE_PERSONA_DOC = {
    "requestId": SAMPLE_REQUEST_ID,
    "sentiment": "positive",
    "keywords": ["testing", "quality", "software"],
    "wordCount": 20
}

# --- Test Cases ---

def test_generate_not_found(client):
    """
    Test that POST /generate/{request_id} returns 404 for a non-existent ID.
    """
    response = client.post(f"/generate/non-existent-id", json={"prompt": "test"})
    assert response.status_code == 404

def test_generate_success(client, mock_db):
    """
    Test successful text generation.
    """
    # Arrange
    mock_db.persona_analysis.insert_one(SAMPLE_PERSONA_DOC.copy())
    prompt = "the future of AI"

    # Act
    response = client.post(f"/generate/{SAMPLE_REQUEST_ID}", json={"prompt": prompt})

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["request_id"] == SAMPLE_REQUEST_ID

    # Check that the generated text reflects the persona
    generated_text = response_data["text"]
    assert prompt in generated_text
    assert "great" in generated_text # From the "positive" sentiment

    # Check that one of the keywords is in the text
    keyword_present = any(kw in generated_text for kw in SAMPLE_PERSONA_DOC["keywords"])
    assert keyword_present, "Generated text should contain one of the persona's keywords"
