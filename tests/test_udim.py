import os
import json
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient
import persona_pb2
from google.protobuf.json_format import Parse

# Test constants
TEST_AWS_REGION = "us-east-1"
TEST_S3_BUCKET = "test-echosphere-bucket"
TEST_SQS_QUEUE = "test-echosphere-queue"


@mock_aws
def test_ingest_data_with_aws_services():
    # 1. Set up mock environment
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = TEST_AWS_REGION
    os.environ["S3_BUCKET"] = TEST_S3_BUCKET

    # 2. Set up mock AWS resources
    s3_client = boto3.client("s3", region_name=TEST_AWS_REGION)
    sqs_client = boto3.client("sqs", region_name=TEST_AWS_REGION)

    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)
    queue_response = sqs_client.create_queue(QueueName=TEST_SQS_QUEUE)
    queue_url = queue_response["QueueUrl"]
    os.environ["SQS_QUEUE_URL"] = queue_url

    # 3. Import the app and create the client AFTER mocks are set up
    from echosystem.udim.main import app
    client = TestClient(app)

    # 4. Prepare and call the endpoint
    test_payload = {"text": "This is a test ingestion for the full protobuf pipeline."}
    response = client.post("/ingest", json=test_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"

    # 5. Verify S3 upload (as Protobuf)
    s3_key = response_data["s3_key"]
    s3_object = s3_client.get_object(Bucket=TEST_S3_BUCKET, Key=s3_key)
    assert s3_object['ContentType'] == 'application/protobuf'

    ingestion_request_proto = persona_pb2.IngestionRequest()
    ingestion_request_proto.ParseFromString(s3_object["Body"].read())
    assert ingestion_request_proto.text == test_payload["text"]

    # 6. Verify SQS message (as JSON representation of Protobuf)
    messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)["Messages"]
    assert len(messages) == 1

    ingestion_event_proto = Parse(messages[0]["Body"], persona_pb2.IngestionEvent())
    assert ingestion_event_proto.s3_bucket == TEST_S3_BUCKET
    assert ingestion_event_proto.s3_key == s3_key

    # 7. Clean up environment variables
    del os.environ["AWS_REGION"]
    del os.environ["S3_BUCKET"]
    del os.environ["SQS_QUEUE_URL"]
