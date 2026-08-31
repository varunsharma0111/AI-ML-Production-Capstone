"""Prometheus metrics instrumentation middleware and registry for API, DB, Redis, Worker, S3, and Inference."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# HTTP API Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total count of HTTP requests handled by the API",
    ["method", "handler", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency histogram in seconds",
    ["method", "handler"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# DB & Redis Health Metrics
DB_POOL_CONNECTIONS = Gauge(
    "db_pool_connections",
    "Current database connection pool stats",
    ["state"],  # "checkedin", "checkedout", "overflow"
)

REDIS_QUEUE_DEPTH = Gauge(
    "redis_queue_depth",
    "Current depth of Redis job queue",
    ["queue_name"],
)

# Async Worker & Jobs Metrics
JOBS_TOTAL = Counter(
    "jobs_total",
    "Total count of background jobs processed",
    ["job_type", "status"],
)

JOB_DURATION_SECONDS = Histogram(
    "job_duration_seconds",
    "Job execution duration in seconds",
    ["job_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

TRAINING_DURATION_SECONDS = Histogram(
    "training_duration_seconds",
    "Model training duration in seconds",
    ["model_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Inference Metrics
INFERENCE_REQUESTS_TOTAL = Counter(
    "inference_requests_total",
    "Total count of model inference predictions",
    ["status"],  # "success", "failure", "unapproved"
)

INFERENCE_LATENCY_SECONDS = Histogram(
    "inference_latency_seconds",
    "Controlled model inference latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# S3 & Storage Operations Metrics
S3_OPERATIONS_TOTAL = Counter(
    "s3_operations_total",
    "Total count of S3 storage operations",
    ["operation", "status"],  # operation: put, get, delete, head
)


async def prometheus_metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware collecting HTTP request count and latency metrics."""
    path = request.url.path
    if path in ("/health/live", "/health/ready", "/metrics"):
        return await call_next(request)

    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    status_code = str(response.status_code)
    method = request.method
    handler = path

    HTTP_REQUESTS_TOTAL.labels(method=method, handler=handler, status=status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, handler=handler).observe(duration)

    return response


def setup_metrics(app: FastAPI) -> None:
    """Attach metrics middleware and /metrics endpoint to FastAPI application."""
    app.middleware("http")(prometheus_metrics_middleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
