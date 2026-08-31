"""Structured logging with explicit safe fields."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Emit JSON logs with correlation identifiers without serializing request bodies or credentials."""

    safe_fields = {
        "request_id",
        "job_id",
        "workspace_id",
        "correlation_id",
        "dataset_id",
        "model_id",
        "component",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "actor_id",
    }

    sensitive_keywords = {"token", "password", "secret", "access_key", "key", "authorization"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self.safe_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = str(value)

        # Redact sensitive fields if passed in extra
        for k in list(payload.keys()):
            if any(keyword in k.lower() for keyword in self.sensitive_keywords):
                payload[k] = "[REDACTED]"

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Configure process logging once at startup."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
