"""Redis client helper for ephemeral job coordination and Pub/Sub channel notifications."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages ephemeral Redis coordination for background worker channels."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url
        self._is_connected = False

    async def connect(self) -> None:
        if self._redis_url:
            logger.info("Connecting to Redis at %s", self._redis_url)
            self._is_connected = True

    async def disconnect(self) -> None:
        if self._is_connected:
            logger.info("Disconnecting from Redis")
            self._is_connected = False

    async def publish_job_update(self, workspace_id: str, payload: dict[str, Any]) -> None:
        """Publish job status event to workspace channel."""
        logger.debug("Broadcasting event to workspace channel %s: %s", workspace_id, payload)
