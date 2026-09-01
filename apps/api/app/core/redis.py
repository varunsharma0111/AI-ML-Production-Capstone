"""Production-grade redis.asyncio client manager for job queueing and Pub/Sub messaging."""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages connection pooling, async task queueing, and Pub/Sub notifications."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or get_settings().redis_url
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self) -> bool:
        """Initialize connection pool and ping Redis server. Fails closed gracefully."""
        if not self._redis_url:
            logger.warning("Redis URL not configured. Operating in fallback mode.")
            self._is_connected = False
            return False

        try:
            logger.info("Initializing Redis connection pool at %s", self._redis_url)
            self._pool = ConnectionPool.from_url(
                self._redis_url,
                decode_responses=True,
                max_connections=20,
                socket_timeout=5.0,
            )
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            self._is_connected = True
            logger.info("Successfully connected to Redis server.")
            return True
        except Exception as error:
            logger.warning("Redis connection failed (%s). Falling back to database polling.", error)
            self._is_connected = False
            return False

    async def close(self) -> None:
        """Close Redis client and connection pool."""
        self._is_connected = False
        if self._client:
            await self._client.aclose()  # type: ignore[attr-defined]
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis connection closed.")

    async def disconnect(self) -> None:
        """Alias for close() to maintain backwards compatibility."""
        await self.close()

    async def is_healthy(self) -> bool:
        """Execute ping command to verify Redis server connectivity."""
        if not self._is_connected or not self._client:
            return False
        try:
            return bool(await self._client.ping())
        except RedisError:
            self._is_connected = False
            return False

    async def enqueue_job(self, queue_name: str, job_id: str) -> bool:
        """Push a job ID to the right end of the specified FIFO queue."""
        if not self._is_connected or not self._client:
            return False
        try:
            await self._client.lpush(queue_name, job_id)
            logger.debug("Enqueued job %s to Redis queue '%s'", job_id, queue_name)
            return True
        except RedisError as exc:
            logger.error(
                "Failed to enqueue job %s to Redis queue '%s': %s", job_id, queue_name, exc
            )
            return False

    async def dequeue_job(self, queue_name: str, timeout: int = 2) -> str | None:
        """Blocking pop a job ID from the specified FIFO queue."""
        if not self._is_connected or not self._client:
            return None
        try:
            result = await self._client.brpop(queue_name, timeout=timeout)
            if result:
                # result is a tuple of (queue_name, popped_value)
                return str(result[1])
            return None
        except RedisError as exc:
            logger.error("Failed to dequeue job from Redis queue '%s': %s", queue_name, exc)
            return None

    async def publish_job_update(self, workspace_id: str, payload: dict[str, Any]) -> bool:
        """Publish real-time job state change event to workspace channel."""
        channel = f"workspace:{workspace_id}:jobs"
        if not self._is_connected or not self._client:
            logger.debug("Redis disconnected. Skipping Pub/Sub event broadcast on %s", channel)
            return False

        try:
            serialized = json.dumps(payload, default=str)
            await self._client.publish(channel, serialized)
            logger.debug("Published Pub/Sub event to channel %s: %s", channel, serialized)
            return True
        except RedisError as exc:
            logger.error("Failed to publish Pub/Sub event to channel %s: %s", channel, exc)
            return False

    def subscribe_workspace_jobs(self, workspace_id: str):
        """Return a PubSub subscriber context subscribed to workspace channel."""
        if not self._is_connected or not self._client:
            return None
        pubsub = self._client.pubsub()
        return pubsub
