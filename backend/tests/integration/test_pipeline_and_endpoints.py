import io
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app, get_container
from app.core.container import Container

def test_health_check_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_rejects_unsupported_file_format(client: TestClient):
    fake_file = io.BytesIO(b"binary docx data")
    response = client.post(
        "/upload",
        files={"file": ("malicious.docx", fake_file, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_rejects_fake_pdf_header(client: TestClient):
    fake_pdf = io.BytesIO(b"NOT A REAL PDF FILE")
    response = client.post(
        "/upload",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")}
    )
    assert response.status_code == 400
    assert "missing %PDF- header" in response.json()["detail"]


def test_upload_rejects_oversized_file(client: TestClient):
    # Simulate file > 25 MB
    large_data = b"%PDF-" + b"0" * (26 * 1024 * 1024)
    response = client.post(
        "/upload",
        files={"file": ("large.pdf", io.BytesIO(large_data), "application/pdf")}
    )
    assert response.status_code == 413
    assert "25 MB" in response.json()["detail"]


def test_ingest_rejects_unauthorized_paths(client: TestClient):
    # Attempting to read outside sample_docs / uploads
    response = client.post("/ingest", json={"file_path": "../../app/main.py"})
    assert response.status_code in [403, 404]

