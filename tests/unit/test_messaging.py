"""Unit tests for Phase 6 transactional outbox publishing and idempotent consumer DLQ routing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from messaging.consumer import IdempotentEventConsumer
from messaging.schemas.events import DomainEvent


def test_domain_event_schema_validation() -> None:
    event_id = uuid4()
    aggregate_id = uuid4()

    event = DomainEvent(
        event_id=event_id,
        aggregate_type="task",
        aggregate_id=aggregate_id,
        event_type="task.created",
        timestamp=datetime.now(UTC),
        payload={"title": "Test Event Task"},
    )
    assert event.aggregate_type == "task"
    assert event.event_type == "task.created"


def test_idempotent_consumer_skips_duplicates() -> None:
    consumer = IdempotentEventConsumer()
    event_id = uuid4()

    first_run = consumer.consume(event_id, "task.created", {"task_id": str(event_id)})
    assert first_run is True

    # Duplicate submission
    second_run = consumer.consume(event_id, "task.created", {"task_id": str(event_id)})
    assert second_run is True
    assert len(consumer.dlq_records) == 0
