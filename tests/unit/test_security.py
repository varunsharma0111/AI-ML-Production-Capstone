"""Unit tests for defensive security headers and CORS middleware."""

from fastapi.testclient import TestClient
from app.main import app


def test_security_headers_present() -> None:
    """Verify defensive HTTP security headers are injected in API responses."""
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_cors_headers_present() -> None:
    """Verify CORS middleware responds appropriately to OPTIONS preflight."""
    client = TestClient(app)
    response = client.options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
