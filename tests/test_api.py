"""Integration tests for FastAPI backend server endpoints.

Validates health check endpoint and document redaction multipart upload API
per backend container requirements.
No inline comments are present in the codebase — documentation is in docstrings.
"""
import os
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_check_endpoint() -> None:
    """Verify /health endpoint returns HTTP 200 and operational status status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data

def test_redact_endpoint_invalid_extension() -> None:
    """Verify endpoint rejects non-docx uploads with HTTP 400."""
    response = client.post(
        "/api/redact",
        files={"file": ("test.txt", b"Hello world", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only .docx files are supported" in response.json()["detail"]

def test_redact_endpoint_valid_docx() -> None:
    """Verify endpoint processes valid .docx file and returns redacted document response."""
    test_docx_path = "Red Herring Prospectus.docx"
    if not os.path.exists(test_docx_path):
        pytest.skip("Test docx file not available in test environment.")
        
    with open(test_docx_path, "rb") as f:
        file_bytes = f.read()
        
    response = client.post(
        "/api/redact",
        files={"file": ("sample.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"locale": "en_US", "recognizer_pack": "in", "score_threshold": "0.7"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "X-Subject-Entity" in response.headers
    assert "X-Total-PII-Count" in response.headers
    assert len(response.content) > 0
