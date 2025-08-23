# Generator Module

This service provides an API that allows a persona to "speak" by generating content based on its learned traits.

## Functionality

- Provides a `POST /generate/{request_id}` endpoint.
- Fetches the analysis document for the given `request_id` from the Persona Knowledge Graph (PKG).
- Takes a `prompt` from the request body.
- Simulates content generation by creating a text response that incorporates the persona's stored `sentiment` and `keywords`.

## Environment Variables

- `MONGO_URI`: The connection URI for the MongoDB database.
- `MONGO_DB_NAME`: The name of the database to use.
