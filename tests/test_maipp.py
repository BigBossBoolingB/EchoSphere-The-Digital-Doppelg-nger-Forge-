import os

import boto3
import mongomock
from google.protobuf.json_format import MessageToJson
from moto import mock_aws

import persona_pb2

# Test constants
TEST_AWS_REGION = "us-east-1"
TEST_S3_BUCKET = "test-maipp-bucket"
TEST_SQS_QUEUE = "test-maipp-queue"
TEST_MONGO_DB_NAME = "test-echosphere-db"


@mock_aws
def test_maipp_pipeline():
    # 1. Set up mock environment
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = TEST_AWS_REGION
    os.environ["S3_BUCKET"] = TEST_S3_BUCKET
    os.environ["MONGO_DB_NAME"] = TEST_MONGO_DB_NAME

    # 2. Set up mock AWS and DB resources
    s3_client = boto3.client("s3", region_name=TEST_AWS_REGION)
    sqs_client = boto3.client("sqs", region_name=TEST_AWS_REGION)
    mock_db_client = mongomock.MongoClient()

    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)
    queue_response = sqs_client.create_queue(QueueName=TEST_SQS_QUEUE)
    queue_url = queue_response["QueueUrl"]
    os.environ["SQS_QUEUE_URL"] = queue_url

    # 3. Create test data and messages
    request_id = "test-request-123"
    s3_key = f"ingestion/{request_id}.protobuf"
    ingestion_request_proto = persona_pb2.IngestionRequest(
        text="This is a great test for the database."
    )
    s3_client.put_object(
        Bucket=TEST_S3_BUCKET,
        Key=s3_key,
        Body=ingestion_request_proto.SerializeToString(),
    )

    ingestion_event_proto = persona_pb2.IngestionEvent(
        request_id=request_id, s3_bucket=TEST_S3_BUCKET, s3_key=s3_key
    )
    sqs_client.send_message(
        QueueUrl=queue_url, MessageBody=MessageToJson(ingestion_event_proto)
    )

    # 4. Run the MAIPP processor, injecting the mock DB client
    from echosystem.maipp import main as maipp_main

    inserted_ids = maipp_main.poll_and_process(db_client=mock_db_client)

    # 5. Assertions on the database
    assert len(inserted_ids) == 1

    db = mock_db_client[TEST_MONGO_DB_NAME]
    analysis_collection = db.persona_analysis

    saved_doc = analysis_collection.find_one({"_id": inserted_ids[0]})

    assert saved_doc is not None
    assert saved_doc["requestId"] == request_id
    assert saved_doc["sentiment"] == "positive"
    assert "great" in saved_doc["keywords"]
    assert "database" in saved_doc["keywords"]
    assert saved_doc["wordCount"] == 8  # Note: MessageToDict converts to camelCase

    # 6. Check if the SQS message was deleted
    response = sqs_client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=2)
    assert "Messages" not in response

    # 7. Clean up environment variables
    del os.environ["AWS_REGION"]
    del os.environ["S3_BUCKET"]
    del os.environ["SQS_QUEUE_URL"]
    del os.environ["MONGO_DB_NAME"]
