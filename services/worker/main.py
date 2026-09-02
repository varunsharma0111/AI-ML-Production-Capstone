"""Background worker process loop with Redis queue consumer."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure workspace root and apps/api directory are present in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
_API_DIR = _ROOT / "apps" / "api"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

# ruff: noqa: E402

import asyncio
import logging
import signal
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from uuid import UUID

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"

    class _DummyMetric:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def inc(self, *args: object, **kwargs: object) -> None:
            pass

        def set(self, *args: object, **kwargs: object) -> None:
            pass

    Counter = Gauge = _DummyMetric  # type: ignore[misc,assignment]

    def generate_latest(registry: Any = None, escaping: str = "") -> bytes:  # type: ignore[misc]
        return b"# prometheus_client not installed\n"


from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.redis import RedisManager
from app.db.repositories.jobs import JobRepository
from app.db.session import create_database_engine, create_session_factory
from app.domains.jobs.types import JobStatus
from services.worker.runner import JobRunner

logger = logging.getLogger(__name__)

# Worker Prometheus Metrics
JOB_QUEUE_DEPTH = Gauge("job_queue_depth", "Current depth of the asynchronous background job queue")
JOB_EXECUTION_FAILURES = Counter(
    "job_execution_failures_total", "Total count of background job execution failures"
)
JOBS_PROCESSED_SUCCESS = Counter(
    "jobs_processed_success_total", "Total count of successfully executed background jobs"
)


class WorkerMetricsHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler exposing Prometheus metrics for worker daemon."""

    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if self.path in ("/metrics", "/metrics/"):
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        elif self.path in ("/health/live", "/health/ready"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Suppress verbose HTTP server logs
        pass


def _start_metrics_server(port: int = 8001) -> HTTPServer:
    """Start threaded HTTP server for metrics scraping."""
    server = HTTPServer(("0.0.0.0", port), WorkerMetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Worker metrics HTTP server running on port %d", port)
    return server


async def process_job_by_id(
    session_factory: async_sessionmaker[AsyncSession],
    redis_manager: RedisManager,
    job_runner: JobRunner,
    job_repo: JobRepository,
    job_id: UUID,
) -> bool:
    """Acquire, execute, and broadcast job state transition."""
    async with session_factory() as session:
        async with session.begin():
            job = await job_repo.get_job_by_id(session, job_id)
            if job is None or job.status not in (JobStatus.QUEUED.value, "queued"):
                logger.debug("Job %s is no longer in QUEUED state. Skipping.", job_id)
                return False

            job.status = JobStatus.PROCESSING.value
            job.started_at = datetime.now(UTC)
            if job.attempt_count is None:
                job.attempt_count = 0
            job.attempt_count += 1
            await session.flush()

            status, result, error = await job_runner.execute_job(session, job)

            workspace_id_str = str(job.workspace_id)
            job_type_str = str(job.job_type)
            result_json = job.result_json
            error_detail = job.error_detail
            final_status = str(job.status)

        # Broadcast state: COMPLETED or FAILED after commit
        await redis_manager.publish_job_update(
            workspace_id_str,
            {
                "event": "job_status",
                "job_id": str(job_id),
                "job_type": job_type_str,
                "status": final_status,
                "result": result_json,
                "error": error_detail,
                "workspace_id": workspace_id_str,
            },
        )

        if status == JobStatus.COMPLETED or final_status == JobStatus.COMPLETED.value:
            JOBS_PROCESSED_SUCCESS.inc()
            logger.info("Successfully finished processing job %s", job_id)
            return True
        else:
            JOB_EXECUTION_FAILURES.inc()
            logger.warning("Job %s finished with status %s", job_id, final_status)
            return True


async def main() -> None:
    import os

    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting Capstone Background Worker Service...")

    metrics_port = int(os.getenv("WORKER_METRICS_PORT", "8001"))
    metrics_server = _start_metrics_server(metrics_port)

    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    redis_manager = RedisManager(settings.redis_url)

    await redis_manager.connect()

    job_repo = JobRepository()
    job_runner = JobRunner(job_repo)

    JOB_QUEUE_DEPTH.set(0)

    stop_event = asyncio.Event()

    def _shutdown_handler() -> None:
        logger.info("Received termination signal. Shutting down worker gracefully...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            pass  # Signal handlers on Windows loop

    logger.info("Worker consumer loop initialized. Ready to process background jobs.")

    while not stop_event.is_set():
        try:
            # 1. Primary: Dequeue job ID from Redis queue
            job_id_str = await redis_manager.dequeue_job("job_queue", timeout=1)
            if job_id_str:
                try:
                    job_id = UUID(job_id_str)
                    await process_job_by_id(
                        session_factory, redis_manager, job_runner, job_repo, job_id
                    )
                except ValueError:
                    logger.error("Invalid job ID popped from Redis queue: %s", job_id_str)
                continue

            # 2. Fallback: Query database for any unhandled QUEUED jobs
            async with session_factory() as session:
                async with session.begin():
                    queued_job = await job_repo.get_next_queued_job(session)
                    queued_id = queued_job.id if queued_job else None

            if queued_id:
                logger.info("Claimed queued job %s via DB fallback polling.", queued_id)
                await process_job_by_id(
                    session_factory, redis_manager, job_runner, job_repo, queued_id
                )
            else:
                await asyncio.sleep(1)

        except Exception as exc:
            logger.exception("Error in worker consumer loop: %s", exc)
            await asyncio.sleep(2)

    await redis_manager.close()
    await engine.dispose()
    metrics_server.shutdown()
    logger.info("Worker service stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
