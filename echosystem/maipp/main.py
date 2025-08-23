import os
import json
import logging
import boto3
import time
import persona_pb2
from google.protobuf.json_format import Parse, MessageToDict
from pymongo import MongoClient

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# AWS and DB Configuration from environment variables
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/echosphere-ingestion-queue")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "echosphere")

def get_db_client():
    """Returns a MongoClient instance."""
    return MongoClient(MONGO_URI)

def analyze_text(text: str) -> persona_pb2.AnalysisFeatures:
    # (This function remains the same)
    logger.info(f"Analyzing text: '{text[:30]}...'")
    words = text.lower().split()
    cleaned_words = [word.strip('.,!?;') for word in words]
    keywords = list(set([word for word in cleaned_words if len(word) >= 4]))
    sentiment = "positive" if "good" in words or "great" in words else "neutral"

    analysis = persona_pb2.AnalysisFeatures(
        sentiment=sentiment,
        keywords=keywords,
        word_count=len(words)
    )
    logger.info(f"Analysis complete: {analysis.sentiment}")
    return analysis

def save_analysis(db_client, request_id: str, analysis_proto: persona_pb2.AnalysisFeatures):
    """Saves the analysis result to the database."""
    db = db_client[MONGO_DB_NAME]
    collection = db.persona_analysis

    # Convert protobuf to a dictionary for MongoDB
    analysis_dict = MessageToDict(analysis_proto)
    analysis_dict["requestId"] = request_id # Add the request_id for tracking

    insert_result = collection.insert_one(analysis_dict)
    logger.info(f"Saved analysis for request_id {request_id} to DB. Inserted ID: {insert_result.inserted_id}")
    return insert_result.inserted_id

def process_message(message: dict, s3_client, db_client):
    """Processes a single SQS message."""
    logger.info(f"Processing message ID: {message['MessageId']}")
    try:
        event_json = message['Body']
        ingestion_event = Parse(event_json, persona_pb2.IngestionEvent())

        # Fetch and parse data from S3
        s3_response = s3_client.get_object(Bucket=ingestion_event.s3_bucket, Key=ingestion_event.s3_key)
        ingestion_request = persona_pb2.IngestionRequest()
        ingestion_request.ParseFromString(s3_response['Body'].read())

        # Perform analysis
        analysis_result = analyze_text(ingestion_request.text)

        # Save to DB
        inserted_id = save_analysis(db_client, ingestion_event.request_id, analysis_result)

        return inserted_id

    except Exception as e:
        logger.error(f"Error processing message {message['MessageId']}: {e}")
        return None

def poll_and_process(db_client=None) -> list:
    """
    Polls SQS, processes messages, saves results to DB, and returns a list of inserted DB IDs.
    Accepts an optional db_client for testing purposes.
    """
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    sqs_client = boto3.client("sqs", region_name=AWS_REGION)

    # Get a db client if one isn't provided
    if db_client is None:
        db_client = get_db_client()

    logger.info(f"Starting to poll SQS queue: {SQS_QUEUE_URL}")

    response = sqs_client.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=1
    )

    inserted_ids = []
    if "Messages" in response:
        logger.info(f"Found {len(response['Messages'])} messages to process.")
        for message in response["Messages"]:
            result_id = process_message(message, s3_client, db_client)
            if result_id:
                inserted_ids.append(result_id)

            receipt_handle = message['ReceiptHandle']
            sqs_client.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"Deleted message ID: {message['MessageId']}")
    else:
        logger.info("No messages in queue.")

    db_client.close() # Close the client connection
    return inserted_ids


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    if not S3_BUCKET:
        raise ValueError("S3_BUCKET environment variable is not set.")

    results = poll_and_process()
    if results:
        logger.info(f"Successfully processed {len(results)} messages. Inserted IDs: {results}")
