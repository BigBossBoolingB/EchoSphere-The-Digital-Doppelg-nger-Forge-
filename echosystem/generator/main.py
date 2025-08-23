import os
import random
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional
from contextlib import asynccontextmanager

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
    yield
    app.state.mongodb_client.close()

app = FastAPI(lifespan=lifespan)

# Dependency to get the DB
def get_db(request):
    return request.app.state.db

# --- Business Logic ---

def generate_text(persona_doc: dict, prompt: str) -> str:
    """
    Simulates text generation based on persona traits.
    """
    sentiment = persona_doc.get("sentiment", "neutral")
    keywords = persona_doc.get("keywords", [])

    if not keywords:
        return f"As a persona with a {sentiment} outlook, I don't have much to say about '{prompt}' yet."

    # Simple generation logic
    chosen_keyword = random.choice(keywords)

    if sentiment == "positive":
        return f"I feel great about '{prompt}'! It reminds me of the importance of {chosen_keyword}."
    else: # neutral or any other sentiment
        return f"When considering '{prompt}', it's important to think about {chosen_keyword}."

# --- API Endpoints ---

@app.post("/generate/{request_id}", response_model=GenerateResponse)
async def generate_from_persona(request_id: str, request: GenerateRequest, db: MongoClient = Depends(get_db)):
    """
    Generates text based on the persona associated with the request_id.
    """
    analysis_doc = db.persona_analysis.find_one({"requestId": request_id})

    if not analysis_doc:
        raise HTTPException(status_code=404, detail=f"Persona analysis for request_id {request_id} not found")

    generated_text = generate_text(analysis_doc, request.prompt)

    return GenerateResponse(
        text=generated_text,
        request_id=request_id
    )
