import os

import boto3
import mongomock
import pytest
from google.protobuf.json_format import MessageToJson
from moto import mock_aws

import persona_pb2

# Test Constants
TEST_AWS_REGION = "us-east-1"
TEST_MONGO_DB_NAME = "test-trainer-db"
REFINEMENT_QUEUE_NAME = "test-refinement-queue-trainer"
SAMPLE_REQUEST_ID = "test-request-trainer-123"


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
    return mongomock.MongoClient()


def test_trainer_pipeline(aws_credentials, mock_db_client):
    # 1. Set up mock environment and resources
    with mock_aws():
        # SQS Setup
        sqs = boto3.client("sqs", region_name=TEST_AWS_REGION)
        queue_url = sqs.create_queue(QueueName=REFINEMENT_QUEUE_NAME)["QueueUrl"]
        os.environ["REFINEMENT_SQS_QUEUE_URL"] = queue_url
        os.environ["AWS_REGION"] = TEST_AWS_REGION

        # DB Setup
        os.environ["MONGO_DB_NAME"] = TEST_MONGO_DB_NAME
        db = mock_db_client[TEST_MONGO_DB_NAME]
        collection = db.persona_analysis

        # 2. Pre-populate DB with a 'refined' document
        refined_doc = {
            "requestId": SAMPLE_REQUEST_ID,
            "status": "refined",
            "sentiment": "positive",
            "keywords": ["approved"],
            "feedback": {"notes": "good"},
        }
        collection.insert_one(refined_doc)

        # 3. Send a refinement event to SQS
        refinement_event = persona_pb2.RefinementEvent(request_id=SAMPLE_REQUEST_ID)
        sqs.send_message(
            QueueUrl=queue_url, MessageBody=MessageToJson(refinement_event)
        )

        # Act
        # 4. Run the trainer processor, injecting the mock DB client
        from echosystem.trainer import main as trainer_main

        trainer_main.poll_and_process(db_client=mock_db_client)

        # Assert
        # 5. Check that the document status was updated in the DB
        final_doc = collection.find_one({"requestId": SAMPLE_REQUEST_ID})
        assert final_doc is not None
        assert final_doc["status"] == "retraining_complete"

        # 6. Check that the SQS message was deleted
        response = sqs.receive_message(QueueUrl=queue_url, WaitTimeSeconds=2)
        assert "Messages" not in response

        # Clean up
        del os.environ["REFINEMENT_SQS_QUEUE_URL"]
        del os.environ["MONGO_DB_NAME"]
        del os.environ["AWS_REGION"]
