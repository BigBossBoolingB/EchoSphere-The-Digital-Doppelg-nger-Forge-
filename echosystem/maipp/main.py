import os
import json
import logging
import boto3
import time

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# AWS Configuration from environment variables
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/echosphere-ingestion-queue")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET") # Expect this to be set by the environment

def analyze_text(text: str) -> dict:
    """
    Simulates AI analysis of the given text.
    """
    logger.info(f"Analyzing text: '{text[:30]}...'")
    words = text.lower().split()
    # Clean words of common punctuation
    cleaned_words = [word.strip('.,!?;') for word in words]
    keywords = list(set([word for word in cleaned_words if len(word) >= 4]))
    sentiment = "positive" if "good" in words or "great" in words else "neutral"

    analysis = {
        "sentiment": sentiment,
        "keywords": keywords[:5],
        "word_count": len(words),
    }
    logger.info(f"Analysis complete: {analysis}")
    return analysis

def process_message(message: dict, s3_client) -> dict:
    """
    Processes a single SQS message, returning the analysis result.
    """
    logger.info(f"Processing message ID: {message['MessageId']}")
    try:
        body = json.loads(message['Body'])
        bucket_name = body['s3_bucket']
        object_key = body['s3_key']

        logger.info(f"Fetching s3://{bucket_name}/{object_key}")
        s3_response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        ingestion_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        text_to_analyze = ingestion_data['text']

        analysis_result = analyze_text(text_to_analyze)

        logger.info(f"PKG Updated for request_id {body['request_id']} with analysis: {analysis_result}")

        return analysis_result

    except Exception as e:
        logger.error(f"Error processing message {message['MessageId']}: {e}")
        return None

def poll_and_process() -> list[dict]:
    """
    Polls the SQS queue for messages, processes them, and returns a list of analysis results.
    """
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    sqs_client = boto3.client("sqs", region_name=AWS_REGION)

    logger.info(f"Starting to poll SQS queue: {SQS_QUEUE_URL}")

    response = sqs_client.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=1
    )

    analysis_results = []
    if "Messages" in response:
        logger.info(f"Found {len(response['Messages'])} messages to process.")
        for message in response["Messages"]:
            result = process_message(message, s3_client)
            if result:
                analysis_results.append(result)

            receipt_handle = message['ReceiptHandle']
            sqs_client.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"Deleted message ID: {message['MessageId']}")
    else:
        logger.info("No messages in queue.")

    return analysis_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    if not S3_BUCKET:
        raise ValueError("S3_BUCKET environment variable is not set.")

    results = poll_and_process()
    if results:
        logger.info(f"Successfully processed {len(results)} messages.")
        for res in results:
            logger.info(f"Result: {res}")
