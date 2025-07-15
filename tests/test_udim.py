from fastapi.testclient import TestClient
from echosystem.udim.main import app
import io

client = TestClient(app)


def test_upload_file():
    """
    Tests the /upload endpoint.
    """
    # Create a dummy file to upload.
    file_content = b"This is a test file."
    file = io.BytesIO(file_content)
    file.name = "test.txt"

    # Create the form data.
    form_data = {
        "user_id": "test_user",
        "data_type": "text",
    }

    # Create the files dictionary.
    files = {"file": (file.name, file, "text/plain")}

    # Send the request.
    response = client.post("/upload", data=form_data, files=files)

    # Check the response.
    assert response.status_code == 200
    assert response.json() == {
        "message": "File 'test.txt' uploaded successfully for user 'test_user' with data type 'text'."
    }
