"""Idempotent event consumer engine with Dead Letter Queue (DLQ) routing."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class IdempotentEventConsumer:
    """Consumes domain events with idempotency tracking and DLQ fallback."""

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self._processed_event_ids: set[UUID] = set()
        self.dlq_records: list[dict[str, Any]] = []

    def consume(self, event_id: UUID, event_type: str, payload: dict[str, Any]) -> bool:
        """Process event idempotently; route to DLQ on failure beyond retry limits."""

        if event_id in self._processed_event_ids:
            logger.info("Skipping duplicate event %s (idempotency hit)", event_id)
            return True

        attempt = 1
        while attempt <= self.max_retries:
            try:
                logger.info(
                    "Consuming event %s (type=%s, attempt=%d)", event_id, event_type, attempt
                )
                # Mark as processed
                self._processed_event_ids.add(event_id)
                return True
            except Exception as exc:
                logger.warning(
                    "Consumer error on event %s (attempt %d): %s", event_id, attempt, exc
                )
                attempt += 1

        # Failure past retry limit -> Route to Dead Letter Queue
        dlq_entry = {
            "event_id": str(event_id),
            "event_type": event_type,
            "payload": payload,
            "error": "Exceeded maximum processing retries.",
        }
        self.dlq_records.append(dlq_entry)
        logger.error("Event %s routed to Dead Letter Queue (DLQ)", event_id)
        return False
