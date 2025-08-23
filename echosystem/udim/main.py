import os
import json
import uuid
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class IngestionData(BaseModel):
    text: str


app = FastAPI()

# Configuration - in a real app, this would be more robust
S3_BUCKET = os.environ.get("S3_BUCKET", "echosphere-persona-data")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/echosphere-ingestion-queue")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

@app.get("/")
async def root():
    return {"message": "Hello from UDIM"}


@app.post("/ingest")
async def ingest_data(data: IngestionData):
    # Instantiate clients inside the function to be compatible with moto
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    sqs_client = boto3.client("sqs", region_name=AWS_REGION)

    request_id = str(uuid.uuid4())
    s3_key = f"ingestion/{request_id}.json"

    try:
        # 1. Upload data to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=data.model_dump_json()
        )

        # 2. Send notification to SQS
        message_body = {
            "request_id": request_id,
            "s3_bucket": S3_BUCKET,
            "s3_key": s3_key,
        }
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )

        return {
            "status": "success",
            "request_id": request_id,
            "s3_key": s3_key
        }
    except Exception as e:
        # In a real app, handle exceptions more gracefully
        raise HTTPException(status_code=500, detail=str(e))
