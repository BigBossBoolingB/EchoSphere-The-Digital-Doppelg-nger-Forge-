# Module for AI Persona Processing (MAIPP)

This module is a message-driven service that performs the initial AI analysis of ingested data.

## Functionality

- Consumes `IngestionEvent` messages from an SQS queue.
- Fetches the corresponding `IngestionRequest` data from S3.
- Performs a simulated AI analysis to extract traits like sentiment and keywords.
- Generates an `AnalysisFeatures` Protobuf message with the results.
- Saves the analysis results as a document in the `persona_analysis` collection in MongoDB.

## Environment Variables

- `SQS_QUEUE_URL`: The URL of the SQS queue for ingestion events.
- `S3_BUCKET`: The name of the S3 bucket where raw data is stored.
- `MONGO_URI`: The connection URI for the MongoDB database.
- `MONGO_DB_NAME`: The name of the database to use.
- `AWS_REGION`: The AWS region for S3 and SQS services.
