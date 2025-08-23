import os
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

# --- Configuration ---
# URLs for downstream services, configured by environment variables
UDIM_URL = os.environ.get("UDIM_URL", "http://localhost:8001")
PTFI_URL = os.environ.get("PTFI_URL", "http://localhost:8002")
GENERATOR_URL = os.environ.get("GENERATOR_URL", "http://localhost:8003")


# --- Pydantic Models for the Public API ---
class CreatePersonaRequest(BaseModel):
    initial_text: str


class GeneratePersonaRequest(BaseModel):
    prompt: str


# --- Authentication ---
async def verify_api_key(x_api_key: str = Header(...)):
    """A simple placeholder for API key authentication."""
    # In a real system, this would involve a secure comparison against a stored secret.
    if x_api_key != "fake-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# --- FastAPI App ---
app = FastAPI()


# --- API Endpoints ---
@app.post("/persona/create", status_code=202)
async def create_persona(
    request: CreatePersonaRequest, api_key: str = Depends(verify_api_key)
):
    """
    Creates a new persona by ingesting initial text.
    Orchestrates a call to the UDIM service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{UDIM_URL}/ingest", json={"text": request.initial_text}
            )
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses
            return response.json()
        except httpx.HTTPStatusError as e:
            # Forward the error from the downstream service
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.json()
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Service unavailable: UDIM - {e}"
            )


@app.get("/persona/{request_id}")
async def get_persona_analysis(
    request_id: str, api_key: str = Depends(verify_api_key)
):
    """
    Retrieves the analysis for a given persona.
    Orchestrates a call to the PTFI service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PTFI_URL}/analysis/{request_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.json()
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Service unavailable: PTFI - {e}"
            )


@app.post("/persona/{request_id}/generate")
async def generate_persona_response(
    request_id: str,
    request: GeneratePersonaRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Generates a response from a persona.
    Orchestrates a call to the Generator service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GENERATOR_URL}/generate/{request_id}",
                json={"prompt": request.prompt},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.json()
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Service unavailable: Generator - {e}"
            )
