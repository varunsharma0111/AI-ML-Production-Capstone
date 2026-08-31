"""Unit tests for RedisManager async queue and Pub/Sub functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.core.redis import RedisManager


@pytest.mark.asyncio
async def test_redis_manager_disabled_fallback() -> None:
    manager = RedisManager(redis_url="")
    connected = await manager.connect()
    assert connected is False
    assert manager.is_connected is False

    healthy = await manager.is_healthy()
    assert healthy is False

    enqueued = await manager.enqueue_job("job_queue", "job_123")
    assert enqueued is False

    dequeued = await manager.dequeue_job("job_queue")
    assert dequeued is None

    published = await manager.publish_job_update("ws_1", {"event": "test"})
    assert published is False


@pytest.mark.asyncio
async def test_redis_manager_mocked_success() -> None:
    with (
        patch("app.core.redis.ConnectionPool.from_url"),
        patch("app.core.redis.Redis") as mock_redis_cls,
    ):
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.lpush = AsyncMock(return_value=1)
        mock_client.brpop = AsyncMock(return_value=("job_queue", "job_999"))
        mock_client.publish = AsyncMock(return_value=1)
        mock_redis_cls.return_value = mock_client

        manager = RedisManager(redis_url="redis://localhost:6379/0")
        connected = await manager.connect()

        assert connected is True
        assert manager.is_connected is True

        healthy = await manager.is_healthy()
        assert healthy is True

        enqueued = await manager.enqueue_job("job_queue", "job_999")
        assert enqueued is True
        mock_client.lpush.assert_called_once_with("job_queue", "job_999")

        dequeued = await manager.dequeue_job("job_queue", timeout=1)
        assert dequeued == "job_999"

        published = await manager.publish_job_update("ws_001", {"status": "processing"})
        assert published is True

        await manager.close()
        assert manager.is_connected is False
