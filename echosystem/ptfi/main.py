import os
import boto3
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Optional
from contextlib import asynccontextmanager
import persona_pb2
from google.protobuf.json_format import MessageToJson

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
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    request_id: str = Field(..., alias="requestId")
    sentiment: str
    keywords: List[str]
    word_count: int = Field(..., alias="wordCount")
    feedback: Optional[dict] = None


# --- App and DB/SQS Setup ---

# Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "echosphere")
REFINEMENT_SQS_QUEUE_URL = os.environ.get("REFINEMENT_SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.mongodb_client = MongoClient(MONGO_URI)
    app.state.db = app.state.mongodb_client[MONGO_DB_NAME]
    app.state.sqs_client = boto3.client("sqs", region_name=AWS_REGION)
    yield
    # Shutdown
    app.state.mongodb_client.close()

app = FastAPI(lifespan=lifespan)

# Dependencies
def get_db(request):
    return request.app.state.db

def get_sqs_client(request):
    return request.app.state.sqs_client

# --- API Endpoints ---

@app.get("/analysis/{request_id}", response_model=AnalysisResult, response_model_by_alias=True)
async def get_analysis(request_id: str, db: MongoClient = Depends(get_db)):
    analysis_doc = db.persona_analysis.find_one({"requestId": request_id})
    if analysis_doc:
        return analysis_doc
    raise HTTPException(status_code=404, detail=f"Analysis for request_id {request_id} not found")

@app.post("/analysis/{request_id}/refine")
async def refine_analysis(request_id: str, refinement: RefinementData, db: MongoClient = Depends(get_db), sqs_client = Depends(get_sqs_client)):
    # 1. Update the document in the database
    update_result = db.persona_analysis.update_one(
        {"requestId": request_id},
        {"$set": {"feedback": refinement.model_dump(), "status": "refined"}}
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Analysis for request_id {request_id} not found")

    # 2. Send an SQS event to trigger retraining
    if not REFINEMENT_SQS_QUEUE_URL:
        # If no queue is configured, just log it. This allows the API to function
        # without the full eventing system being set up.
        import logging
        logging.warning("REFINEMENT_SQS_QUEUE_URL not set. Skipping event notification.")
    else:
        refinement_event = persona_pb2.RefinementEvent(request_id=request_id)
        sqs_client.send_message(
            QueueUrl=REFINEMENT_SQS_QUEUE_URL,
            MessageBody=MessageToJson(refinement_event)
        )

    return {"status": "success", "message": f"Refinement added and retraining event sent for request_id {request_id}"}
