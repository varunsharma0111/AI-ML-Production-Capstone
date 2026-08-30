"""Unit tests for Prometheus metrics collection on API and Worker."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from app.main import app
from fastapi.testclient import TestClient

from services.worker.main import WorkerMetricsHandler


def test_api_metrics_endpoint() -> None:
    """Test that FastAPI exposes /metrics with valid Prometheus exposition format."""
    client = TestClient(app)

    # Perform a request to generate metrics
    health_resp = client.get("/health/live")
    assert health_resp.status_code == 200

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    assert "text/plain" in metrics_resp.headers["content-type"]

    content = metrics_resp.text
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content


def test_worker_metrics_handler() -> None:
    """Test that Worker HTTP metrics handler returns valid Prometheus metrics."""

    class MockSocket:
        def makefile(self, *args: Any, **kwargs: Any) -> BytesIO:
            return BytesIO(b"GET /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n")

    class TestHandler(WorkerMetricsHandler):
        def __init__(self) -> None:
            self.rfile = BytesIO(b"GET /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n")
            self.wfile = BytesIO()
            self.requestline = "GET /metrics HTTP/1.1"
            self.command = "GET"
            self.path = "/metrics"
            self.request_version = "HTTP/1.1"
            self.headers = {}  # type: ignore[assignment]
            self.do_GET()

    handler = TestHandler()
    wfile_buf: Any = handler.wfile
    response_data = cast_bytes(wfile_buf.getvalue())
    assert "200 OK" in response_data
    assert "job_queue_depth" in response_data
    assert "job_execution_failures_total" in response_data


def cast_bytes(data: bytes) -> str:
    return data.decode("utf-8")
