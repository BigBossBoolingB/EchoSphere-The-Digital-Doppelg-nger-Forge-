import os
import json
import boto3
from moto import mock_aws
import pytest
import persona_pb2

# Test constants
TEST_AWS_REGION = "us-east-1"
TEST_S3_BUCKET = "test-maipp-bucket"
TEST_SQS_QUEUE = "test-maipp-queue"

@mock_aws
def test_maipp_pipeline():
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

    # 3. Create test data and messages
    request_id = "test-request-123"
    s3_key = f"ingestion/{request_id}.json"
    s3_content = {"text": "This is a great test."}

    s3_client.put_object(
        Bucket=TEST_S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(s3_content)
    )

    sqs_message_body = {
        "request_id": request_id,
        "s3_bucket": TEST_S3_BUCKET,
        "s3_key": s3_key,
    }
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(sqs_message_body)
    )

    # 4. Run the MAIPP processor
    from echosystem.maipp import main as maipp_main
    analysis_results = maipp_main.poll_and_process()

    # 5. Assertions on the return value
    assert len(analysis_results) == 1
    result = analysis_results[0]
    assert isinstance(result, persona_pb2.AnalysisFeatures)
    assert result.sentiment == "positive"
    assert "great" in result.keywords
    assert "test" in result.keywords
    assert result.word_count == 5

    # 6. Check if the message was deleted
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        WaitTimeSeconds=2
    )
    assert "Messages" not in response

    # 7. Clean up environment variables
    del os.environ["AWS_REGION"]
    del os.environ["S3_BUCKET"]
    del os.environ["SQS_QUEUE_URL"]
