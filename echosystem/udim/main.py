import os
import json
import uuid
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import persona_pb2

# Get a logger instance for this module
import logging
logger = logging.getLogger(__name__)

# Pydantic model for a web-friendly JSON API
class IngestionData(BaseModel):
    text: str


app = FastAPI()

# AWS Configuration from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET", "echosphere-persona-data")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/echosphere-ingestion-queue")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


@app.get("/")
async def root():
    return {"message": "Hello from UDIM"}


@app.post("/ingest")
async def ingest_data(data: IngestionData):
    """
    Ingests data, stores it in S3 as a Protobuf message,
    and sends a notification to SQS, also as a Protobuf message.
    """
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    sqs_client = boto3.client("sqs", region_name=AWS_REGION)

    request_id = str(uuid.uuid4())
    s3_key = f"ingestion/{request_id}.protobuf" # Changed extension to reflect content

    try:
        # 1. Create and serialize the IngestionRequest protobuf for S3
        ingestion_request_proto = persona_pb2.IngestionRequest(text=data.text)
        s3_body = ingestion_request_proto.SerializeToString()

        # 2. Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=s3_body,
            ContentType='application/protobuf'
        )
        logger.info(f"Successfully uploaded data to s3://{S3_BUCKET}/{s3_key}")

        # 3. Create and serialize the IngestionEvent protobuf for SQS
        ingestion_event_proto = persona_pb2.IngestionEvent(
            request_id=request_id,
            s3_bucket=S3_BUCKET,
            s3_key=s3_key
        )
        # SQS message body must be a string. We can send raw bytes,
        # but often it's base64 encoded for safety across systems.
        # For this internal system, sending the raw string of bytes is fine
        # if the receiver expects it, but let's stick to a common pattern.
        # However, SQS boto3's `send_message` expects a string MessageBody.
        # A simple approach is to just use the protobuf JSON format for the message body.
        from google.protobuf.json_format import MessageToJson
        message_body_json = MessageToJson(ingestion_event_proto)

        # 4. Send notification to SQS
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=message_body_json
        )
        logger.info(f"Successfully sent event to SQS for request_id {request_id}")

        return {
            "status": "success",
            "request_id": request_id,
            "s3_key": s3_key
        }
    except Exception as e:
        logger.error(f"Failed to process ingestion request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
