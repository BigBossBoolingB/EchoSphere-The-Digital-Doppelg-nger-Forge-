import os

import boto3
import mongomock
import pytest
from google.protobuf.json_format import MessageToJson

import persona_pb2

# Test Constants
TEST_AWS_REGION = "us-east-1"
TEST_MONGO_DB_NAME = "test-maipp-db"
TEST_S3_BUCKET = "test-maipp-s3-bucket"
REFINEMENT_QUEUE_NAME = "test-maipp-sqs-queue"
SAMPLE_REQUEST_ID = "test-request-maipp-123"


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


def test_maipp_pipeline(aws_credentials, mock_db_client):
    # Arrange
    from moto import mock_aws

    with mock_aws():
        # 1. Set up mock environment and resources
        sqs = boto3.client("sqs", region_name=TEST_AWS_REGION)
        s3 = boto3.client("s3", region_name=TEST_AWS_REGION)

        os.environ["AWS_REGION"] = TEST_AWS_REGION
        os.environ["S3_BUCKET"] = TEST_S3_BUCKET
        os.environ["MONGO_DB_NAME"] = TEST_MONGO_DB_NAME
        queue_url = sqs.create_queue(QueueName=REFINEMENT_QUEUE_NAME)["QueueUrl"]
        os.environ["SQS_QUEUE_URL"] = queue_url
        s3.create_bucket(Bucket=TEST_S3_BUCKET)

        # 2. Create test data and messages
        s3_key = f"ingestion/{SAMPLE_REQUEST_ID}.protobuf"
        ingestion_request = persona_pb2.IngestionRequest(
            text="This is a great test for history."
        )
        s3.put_object(
            Bucket=TEST_S3_BUCKET, Key=s3_key, Body=ingestion_request.SerializeToString()
        )

        ingestion_event = persona_pb2.IngestionEvent(
            request_id=SAMPLE_REQUEST_ID, s3_bucket=TEST_S3_BUCKET, s3_key=s3_key
        )
        sqs.send_message(QueueUrl=queue_url, MessageBody=MessageToJson(ingestion_event))

        # Act: Import module here, after env vars are set
        from echosystem.maipp import main as maipp_main
        inserted_ids = maipp_main.poll_and_process(db_client=mock_db_client)

        # Assert
        assert len(inserted_ids) == 1
        db = mock_db_client[TEST_MONGO_DB_NAME]
        saved_doc = db.persona_analysis.find_one({"_id": inserted_ids[0]})

        assert saved_doc is not None
        assert saved_doc["requestId"] == SAMPLE_REQUEST_ID
        assert saved_doc["status"] == "analysis_complete"

        # Assert history array
        assert "history" in saved_doc
        assert len(saved_doc["history"]) == 1
        creation_event = saved_doc["history"][0]
        assert creation_event["eventType"] == "creation"
        assert "timestamp" in creation_event

        # Assert latest_analysis block
        latest_analysis = saved_doc["latest_analysis"]
        assert latest_analysis["sentiment"] == "positive"
        assert "great" in latest_analysis["keywords"]
        assert "history" in latest_analysis["keywords"]

        # Clean up
        del os.environ["SQS_QUEUE_URL"]
        del os.environ["MONGO_DB_NAME"]
        del os.environ["AWS_REGION"]
        del os.environ["S3_BUCKET"]
