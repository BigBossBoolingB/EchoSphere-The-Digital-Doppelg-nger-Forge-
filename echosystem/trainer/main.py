import os
import logging
import boto3
import time
import persona_pb2
from google.protobuf.json_format import Parse
from pymongo import MongoClient

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
REFINEMENT_SQS_QUEUE_URL = os.environ.get("REFINEMENT_SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "echosphere")

def get_db_client():
    """Returns a MongoClient instance."""
    return MongoClient(MONGO_URI)

def process_refinement_event(message: dict, db_client):
    """
    Processes a single refinement event from SQS.
    """
    logger.info(f"Processing refinement event for message ID: {message['MessageId']}")
    try:
        # 1. Parse the RefinementEvent from the SQS message body
        event_json = message['Body']
        refinement_event = Parse(event_json, persona_pb2.RefinementEvent())
        request_id = refinement_event.request_id

        # 2. Fetch the refined document from the DB
        db = db_client[MONGO_DB_NAME]
        collection = db.persona_analysis
        analysis_doc = collection.find_one({"requestId": request_id})

        if not analysis_doc:
            logger.error(f"Analysis document for request_id {request_id} not found. Cannot retrain.")
            return

        if analysis_doc.get("status") != "refined":
            logger.warning(f"Document for {request_id} is not in 'refined' state. Skipping.")
            return

        # 3. Simulate model retraining
        logger.info(f"Simulating retraining for persona based on feedback for request_id: {request_id}")
        time.sleep(1) # Simulate work

        # 4. Update the document status
        collection.update_one(
            {"_id": analysis_doc["_id"]},
            {"$set": {"status": "retraining_complete"}}
        )
        logger.info(f"Retraining complete for request_id: {request_id}. Status updated.")

    except Exception as e:
        logger.error(f"Error processing refinement event {message['MessageId']}: {e}")

def poll_and_process(db_client=None):
    """
    Polls the refinement SQS queue and processes messages.
    """
    close_db_client = False
    if db_client is None:
        db_client = get_db_client()
        close_db_client = True

    sqs_client = boto3.client("sqs", region_name=AWS_REGION)

    logger.info(f"Starting to poll refinement queue: {REFINEMENT_SQS_QUEUE_URL}")

    response = sqs_client.receive_message(
        QueueUrl=REFINEMENT_SQS_QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=1
    )

    if "Messages" in response:
        for message in response["Messages"]:
            process_refinement_event(message, db_client)

            receipt_handle = message['ReceiptHandle']
            sqs_client.delete_message(
                QueueUrl=REFINEMENT_SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
    else:
        logger.info("No refinement events in queue.")

    if close_db_client:
        db_client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    if not REFINEMENT_SQS_QUEUE_URL:
        raise ValueError("REFINEMENT_SQS_QUEUE_URL environment variable is not set.")

    poll_and_process()
