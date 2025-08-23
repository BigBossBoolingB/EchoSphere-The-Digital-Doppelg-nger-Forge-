import os

import boto3
import mongomock
import pytest
from google.protobuf.json_format import MessageToJson
from unittest.mock import MagicMock

import persona_pb2
from echosystem.aiproxy.client import AIClient

# Test Constants
TEST_AWS_REGION = "us-east-1"
TEST_MONGO_DB_NAME = "test-maipp-db"
TEST_S3_BUCKET = "test-maipp-s3-bucket"
SQS_QUEUE_NAME = "test-maipp-sqs-queue"
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

    # 1. Mock the AI Client
    mock_ai_client = MagicMock(spec=AIClient)
    mock_analysis_result = persona_pb2.AnalysisFeatures(
        sentiment="mock_positive",
        keywords=["mock", "keyword"],
        word_count=2,
    )
    mock_ai_client.get_text_analysis.return_value = mock_analysis_result

    with mock_aws():
        # 2. Set up mock environment and resources
        sqs = boto3.client("sqs", region_name=TEST_AWS_REGION)
        s3 = boto3.client("s3", region_name=TEST_AWS_REGION)

        os.environ["AWS_REGION"] = TEST_AWS_REGION
        os.environ["S3_BUCKET"] = TEST_S3_BUCKET
        os.environ["MONGO_DB_NAME"] = TEST_MONGO_DB_NAME
        queue_url = sqs.create_queue(QueueName=SQS_QUEUE_NAME)["QueueUrl"]
        os.environ["SQS_QUEUE_URL"] = queue_url
        s3.create_bucket(Bucket=TEST_S3_BUCKET)

        # 3. Create test data and messages
        s3_key = f"ingestion/{SAMPLE_REQUEST_ID}.protobuf"
        ingestion_request = persona_pb2.IngestionRequest(text="Some text to analyze.")
        s3.put_object(
            Bucket=TEST_S3_BUCKET, Key=s3_key, Body=ingestion_request.SerializeToString()
        )

        ingestion_event = persona_pb2.IngestionEvent(
            request_id=SAMPLE_REQUEST_ID, s3_bucket=TEST_S3_BUCKET, s3_key=s3_key
        )
        sqs.send_message(QueueUrl=queue_url, MessageBody=MessageToJson(ingestion_event))

        # Act: Import module here, after env vars are set
        from echosystem.maipp import main as maipp_main
        inserted_ids = maipp_main.poll_and_process(
            db_client=mock_db_client, ai_client=mock_ai_client
        )

        # Assert
        mock_ai_client.get_text_analysis.assert_called_once_with("Some text to analyze.")
        assert len(inserted_ids) == 1
        db = mock_db_client[TEST_MONGO_DB_NAME]
        saved_doc = db.persona_analysis.find_one({"_id": inserted_ids[0]})
        assert saved_doc is not None
        assert saved_doc["latest_analysis"]["sentiment"] == "mock_positive"

        # Clean up
        del os.environ["SQS_QUEUE_URL"]
        del os.environ["MONGO_DB_NAME"]
        del os.environ["AWS_REGION"]
        del os.environ["S3_BUCKET"]
