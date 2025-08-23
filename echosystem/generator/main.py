import os
from contextlib import asynccontextmanager

from echosystem.aiproxy.client import AIClient
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

# Pydantic Models
class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    text: str
    request_id: str


# --- App and DB Setup ---

# Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "echosphere")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongodb_client = MongoClient(MONGO_URI)
    app.state.db = app.state.mongodb_client[MONGO_DB_NAME]
    app.state.ai_client = AIClient()
    yield
    app.state.mongodb_client.close()


app = FastAPI(lifespan=lifespan)


# Dependencies
def get_db(request):
    return request.app.state.db


def get_ai_client(request):
    return request.app.state.ai_client


# --- API Endpoints ---


@app.post("/generate/{request_id}", response_model=GenerateResponse)
async def generate_from_persona(
    request_id: str,
    request: GenerateRequest,
    db: MongoClient = Depends(get_db),
    ai_client: AIClient = Depends(get_ai_client),
):
    """
    Generates text based on the persona associated with the request_id.
    """
    analysis_doc = db.persona_analysis.find_one({"requestId": request_id})

    if not analysis_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Persona analysis for request_id {request_id} not found",
        )

    # Use the AI Proxy to generate text
    generated_text = ai_client.generate_response(analysis_doc, request.prompt)

    return GenerateResponse(text=generated_text, request_id=request_id)
