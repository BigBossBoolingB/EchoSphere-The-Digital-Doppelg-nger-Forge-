import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from echosystem.nexus.main import GENERATOR_URL, PTFI_URL, UDIM_URL, app

# --- Fixtures ---


@pytest.fixture
def client():
    """Fixture to create a TestClient for the Nexus app."""
    with TestClient(app) as test_client:
        yield test_client


# --- Test Cases ---


def test_authentication_missing(client):
    """Test that a request without an API key is rejected."""
    response = client.post("/persona/create", json={"initial_text": "test"})
    assert response.status_code == 422  # FastAPI returns 422 for missing headers


def test_authentication_invalid(client):
    """Test that a request with an invalid API key is rejected."""
    headers = {"X-API-Key": "wrong-key"}
    response = client.post(
        "/persona/create", json={"initial_text": "test"}, headers=headers
    )
    assert response.status_code == 401


@respx.mock
def test_create_persona_orchestration(client):
    """Test that the create endpoint correctly calls the UDIM service."""
    # Mock the downstream service
    udim_route = respx.post(f"{UDIM_URL}/ingest").mock(
        return_value=Response(202, json={"status": "success", "request_id": "123"})
    )

    headers = {"X-API-Key": "fake-secret-key"}
    payload = {"initial_text": "Hello world"}

    # Act
    response = client.post("/persona/create", json=payload, headers=headers)

    # Assert
    assert udim_route.called, "UDIM service was not called"
    assert udim_route.call_count == 1
    assert response.status_code == 202
    assert response.json()["request_id"] == "123"


@respx.mock
def test_get_persona_orchestration(client):
    """Test that the get endpoint correctly calls the PTFI service."""
    request_id = "abc-123"
    ptfi_route = respx.get(f"{PTFI_URL}/analysis/{request_id}").mock(
        return_value=Response(
            200, json={"requestId": request_id, "sentiment": "positive"}
        )
    )

    headers = {"X-API-Key": "fake-secret-key"}

    # Act
    response = client.get(f"/persona/{request_id}", headers=headers)

    # Assert
    assert ptfi_route.called
    assert response.status_code == 200
    assert response.json()["sentiment"] == "positive"


@respx.mock
def test_generate_persona_orchestration(client):
    """Test that the generate endpoint correctly calls the Generator service."""
    request_id = "abc-123"
    generator_route = respx.post(f"{GENERATOR_URL}/generate/{request_id}").mock(
        return_value=Response(200, json={"text": "Generated text"})
    )

    headers = {"X-API-Key": "fake-secret-key"}
    payload = {"prompt": "test prompt"}

    # Act
    response = client.post(
        f"/persona/{request_id}/generate", json=payload, headers=headers
    )

    # Assert
    assert generator_route.called
    assert response.status_code == 200
    assert response.json()["text"] == "Generated text"


@respx.mock
def test_downstream_error_forwarding(client):
    """Test that a 404 from a downstream service is forwarded correctly."""
    request_id = "not-found-id"
    ptfi_route = respx.get(f"{PTFI_URL}/analysis/{request_id}").mock(
        return_value=Response(404, json={"detail": "Analysis not found"})
    )

    headers = {"X-API-Key": "fake-secret-key"}

    # Act
    response = client.get(f"/persona/{request_id}", headers=headers)

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"]["detail"] == "Analysis not found"
