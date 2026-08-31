"""Tests for background worker process job execution and metrics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.entities import Job
from app.domains.jobs.types import JobStatus, JobType

from services.worker.main import process_job_by_id


@pytest.mark.asyncio
async def test_process_job_by_id_success() -> None:
    job_id = uuid4()
    workspace_id = uuid4()

    mock_job = Job(
        id=job_id,
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        job_type=JobType.SAMPLE_ML_INGESTION.value,
        payload_json={"batch_size": 100},
        status=JobStatus.QUEUED.value,
        max_retries=3,
        attempt_count=0,
        version=1,
    )

    mock_session = AsyncMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock(return_value=None)
    session_factory = MagicMock(return_value=session_ctx)

    mock_redis = AsyncMock()
    mock_redis.publish_job_update = AsyncMock(return_value=True)

    mock_runner = AsyncMock()
    mock_runner.execute_job = AsyncMock(return_value=(JobStatus.COMPLETED, {"records": 100}, None))

    mock_repo = AsyncMock()
    mock_repo.get_job_by_id = AsyncMock(return_value=mock_job)

    result = await process_job_by_id(
        session_factory=session_factory,
        redis_manager=mock_redis,
        job_runner=mock_runner,
        job_repo=mock_repo,
        job_id=job_id,
    )

    assert result is True
    assert mock_redis.publish_job_update.call_count == 2
    mock_runner.execute_job.assert_called_once()


@pytest.mark.asyncio
async def test_prevent_duplicate_worker_execution() -> None:
    job_id = uuid4()
    workspace_id = uuid4()

    mock_job = Job(
        id=job_id,
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        job_type=JobType.SAMPLE_ML_INGESTION.value,
        payload_json={"batch_size": 100},
        status=JobStatus.QUEUED.value,
        max_retries=3,
        attempt_count=0,
        version=1,
    )

    mock_session = AsyncMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock(return_value=None)
    session_factory = MagicMock(return_value=session_ctx)

    mock_redis = AsyncMock()
    mock_redis.publish_job_update = AsyncMock(return_value=True)

    mock_runner = AsyncMock()

    async def _execute_job_side_effect(session, job):
        job.status = JobStatus.COMPLETED.value
        return (JobStatus.COMPLETED, {"records": 100}, None)

    mock_runner.execute_job.side_effect = _execute_job_side_effect

    mock_repo = AsyncMock()
    mock_repo.get_job_by_id = AsyncMock(return_value=mock_job)

    # Worker 1 claims and starts job
    w1_task = process_job_by_id(
        session_factory=session_factory,
        redis_manager=mock_redis,
        job_runner=mock_runner,
        job_repo=mock_repo,
        job_id=job_id,
    )

    # Worker 2 attempts to claim the exact same job concurrently
    w2_task = process_job_by_id(
        session_factory=session_factory,
        redis_manager=mock_redis,
        job_runner=mock_runner,
        job_repo=mock_repo,
        job_id=job_id,
    )

    w1_result = await w1_task
    w2_result = await w2_task

    # Exactly ONE worker claims and executes the job
    assert w1_result is True
    assert w2_result is False

    # Verify execution ran exactly once
    assert mock_runner.execute_job.call_count == 1

    # Verify final status is COMPLETED
    assert mock_job.status == JobStatus.COMPLETED.value
