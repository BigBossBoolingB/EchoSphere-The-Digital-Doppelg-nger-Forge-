# User Data Ingestion Module (UDIM)

This service is the primary entrypoint for ingesting new persona data into the EchoSphere ecosystem.

## Functionality

- Provides a `/ingest` HTTP POST endpoint.
- Accepts a JSON payload containing the raw text to be analyzed.
- Creates a unique `request_id` for tracking.
- Stores the raw data as a serialized `IngestionRequest` Protobuf message in an S3 bucket.
- Sends an `IngestionEvent` Protobuf message (as JSON) to an SQS queue to trigger the next stage of processing (MAIPP).

## Environment Variables

- `S3_BUCKET`: The name of the S3 bucket to store the raw data.
- `SQS_QUEUE_URL`: The URL of the SQS queue for ingestion events.
- `AWS_REGION`: The AWS region for the S3 and SQS services.
