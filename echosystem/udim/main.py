from fastapi import FastAPI
from pydantic import BaseModel


class IngestionData(BaseModel):
    text: str

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from UDIM"}


@app.post("/ingest")
async def ingest_data(data: IngestionData):
    return {"status": "success", "data_received": data.model_dump()}
