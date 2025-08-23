import os

import boto3
import mongomock
import pytest
from fastapi.testclient import TestClient
from google.protobuf.json_format import Parse
from moto import mock_aws

import persona_pb2

# --- Test Constants ---
TEST_AWS_REGION = "us-east-1"
TEST_MONGO_DB_NAME = "test-echosphere-db"
REFINEMENT_QUEUE_NAME = "test-refinement-queue"
SAMPLE_REQUEST_ID = "test-request-ptfi-123"
SAMPLE_DOC = {
    "requestId": SAMPLE_REQUEST_ID,
    "sentiment": "neutral",
    "keywords": ["sample", "data"],
    "wordCount": 3,
}

# --- Fixtures ---


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def mock_db_client():
    """Fixture to create a mongomock client instance."""
    return mongomock.MongoClient().db


@pytest.fixture
def client(aws_credentials, mock_db_client):
    """
    Fixture to create a TestClient for the FastAPI app, with mocked DB and SQS.
    """
    with mock_aws():
        # Set up mock SQS inside the mock_aws context
        sqs = boto3.client("sqs", region_name=TEST_AWS_REGION)
        queue_url = sqs.create_queue(QueueName=REFINEMENT_QUEUE_NAME)["QueueUrl"]
        os.environ["REFINEMENT_SQS_QUEUE_URL"] = queue_url
        os.environ["MONGO_DB_NAME"] = TEST_MONGO_DB_NAME

        from echosystem.ptfi.main import app, get_db, get_sqs_client

        app.dependency_overrides[get_db] = lambda: mock_db_client
        app.dependency_overrides[get_sqs_client] = lambda: sqs

        with TestClient(app) as test_client:
            yield test_client

        # Clean up
        app.dependency_overrides.clear()
        del os.environ["REFINEMENT_SQS_QUEUE_URL"]
        del os.environ["MONGO_DB_NAME"]


# --- Test Cases ---


def test_get_analysis_not_found(client):
    response = client.get("/analysis/non-existent-id")
    assert response.status_code == 404


def test_get_analysis_success(client, mock_db_client):
    inserted = mock_db_client.persona_analysis.insert_one(SAMPLE_DOC.copy())
    response = client.get(f"/analysis/{SAMPLE_REQUEST_ID}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["requestId"] == SAMPLE_REQUEST_ID
    assert response_data["_id"] == str(inserted.inserted_id)


def test_refine_analysis_not_found(client):
    refinement_payload = {"approved_keywords": [], "feedback_notes": ""}
    response = client.post("/analysis/non-existent-id/refine", json=refinement_payload)
    assert response.status_code == 404


def test_refine_analysis_success(client, mock_db_client):
    # Arrange
    mock_db_client.persona_analysis.insert_one(SAMPLE_DOC.copy())
    refinement_payload = {
        "approved_keywords": ["sample", "data"],
        "feedback_notes": "This analysis is approved.",
    }

    # Act
    response = client.post(
        f"/analysis/{SAMPLE_REQUEST_ID}/refine", json=refinement_payload
    )

    # Assert API response
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Assert DB state
    updated_doc = mock_db_client.persona_analysis.find_one(
        {"requestId": SAMPLE_REQUEST_ID}
    )
    assert (
        updated_doc["feedback"]["feedback_notes"]
        == refinement_payload["feedback_notes"]
    )
    assert updated_doc["status"] == "refined"

    # Assert SQS event
    sqs_client = boto3.client("sqs", region_name=TEST_AWS_REGION)
    queue_url = sqs_client.get_queue_url(QueueName=REFINEMENT_QUEUE_NAME)["QueueUrl"]
    messages = sqs_client.receive_message(QueueUrl=queue_url)["Messages"]
    assert len(messages) == 1

    event_proto = Parse(messages[0]["Body"], persona_pb2.RefinementEvent())
    assert event_proto.request_id == SAMPLE_REQUEST_ID
