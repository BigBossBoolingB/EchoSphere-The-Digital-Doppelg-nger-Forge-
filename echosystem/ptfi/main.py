import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Optional
from contextlib import asynccontextmanager

# A helper class to handle MongoDB's ObjectId serialization for Pydantic models
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, *args, **kwargs):
        schema.update(type="string")

# Pydantic Models
class RefinementData(BaseModel):
    approved_keywords: List[str]
    feedback_notes: str

class AnalysisResult(BaseModel):
    # Use ConfigDict for Pydantic V2 configuration
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}, # Kept for compatibility, but custom serializer is preferred
    )

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    request_id: str = Field(..., alias="requestId")
    sentiment: str
    keywords: List[str]
    word_count: int = Field(..., alias="wordCount")
    feedback: Optional[dict] = None

# --- App and DB Setup ---

# DB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "echosphere")

# Use lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.mongodb_client = MongoClient(MONGO_URI)
    app.state.db = app.state.mongodb_client[MONGO_DB_NAME]
    yield
    # Shutdown
    app.state.mongodb_client.close()

app = FastAPI(lifespan=lifespan)

# Dependency to get the DB
def get_db(request):
    return request.app.state.db

# --- API Endpoints ---

@app.get("/analysis/{request_id}", response_model=AnalysisResult, response_model_by_alias=True)
async def get_analysis(request_id: str, db: MongoClient = Depends(get_db)):
    """
    Retrieves a single analysis result by its request_id.
    """
    analysis_doc = db.persona_analysis.find_one({"requestId": request_id})
    if analysis_doc:
        return analysis_doc
    raise HTTPException(status_code=404, detail=f"Analysis for request_id {request_id} not found")

@app.post("/analysis/{request_id}/refine")
async def refine_analysis(request_id: str, refinement: RefinementData, db: MongoClient = Depends(get_db)):
    """
    Adds refinement data to an existing analysis result.
    """
    update_result = db.persona_analysis.update_one(
        {"requestId": request_id},
        {"$set": {"feedback": refinement.model_dump()}}
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Analysis for request_id {request_id} not found")

    return {"status": "success", "message": f"Refinement added for request_id {request_id}"}
