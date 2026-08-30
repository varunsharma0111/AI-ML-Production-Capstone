"""Transactional outbox event publisher engine."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.models.entities import OutboxEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class OutboxPublisher:
    """Polls pending outbox records and publishes events safely."""

    async def stage_event(
        self,
        session: AsyncSession,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, object],
    ) -> OutboxEvent:
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload_json=payload,
            status="pending",
        )
        session.add(event)
        await session.flush()
        return event

    async def publish_pending_events(self, session: AsyncSession) -> int:
        result = await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at.asc())
            .limit(50)
        )
        events = list(result.scalars())

        published_count = 0
        for event in events:
            logger.info(
                "Publishing outbox event %s (type=%s, aggregate=%s)",
                event.id,
                event.event_type,
                event.aggregate_type,
            )
            event.status = "published"
            event.published_at = datetime.now(UTC)
            published_count += 1

        await session.flush()
        return published_count
