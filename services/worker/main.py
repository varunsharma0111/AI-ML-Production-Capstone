"""Background worker main service process loop with Prometheus metrics server."""

import asyncio
import logging
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

# Worker Prometheus Metrics
JOB_QUEUE_DEPTH = Gauge(
    "job_queue_depth",
    "Current depth of the asynchronous background job queue"
)
JOB_EXECUTION_FAILURES = Counter(
    "job_execution_failures_total",
    "Total count of background job execution failures"
)


class WorkerMetricsHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler exposing Prometheus metrics for worker daemon."""

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


def _start_metrics_server(port: int = 8000) -> HTTPServer:
    """Start threaded HTTP server for metrics scraping."""
    server = HTTPServer(("0.0.0.0", port), WorkerMetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Worker metrics HTTP server running on port %d", port)
    return server


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting Capstone Background Worker Service...")

    metrics_server = _start_metrics_server(8000)

    # Initialize gauge metric baseline
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

    while not stop_event.is_set():
        logger.debug("Worker heartbeat polling...")
        await asyncio.sleep(5)

    metrics_server.shutdown()
    logger.info("Worker service stopped.")


if __name__ == "__main__":
    asyncio.run(main())
