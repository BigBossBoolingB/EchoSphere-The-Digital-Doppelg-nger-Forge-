from fastapi.testclient import TestClient
from echosystem.udim.main import app

client = TestClient(app)

def test_ingest_data():
    test_payload = {"text": "This is a test ingestion."}
    response = client.post("/ingest", json=test_payload)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "success"
    assert response_json["data_received"] == test_payload
