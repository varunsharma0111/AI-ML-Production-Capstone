"""Unit tests for Phase 4 job domain enums and schemas."""

from __future__ import annotations

import pytest
from app.api.schemas.jobs import JobSubmit
from app.domains.jobs.types import JobStatus, JobType
from pydantic import ValidationError


def test_job_status_values() -> None:
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.PROCESSING.value == "processing"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"
    assert JobStatus.CANCELLED.value == "cancelled"


def test_job_submit_validation() -> None:
    valid_submit = JobSubmit(
        job_type=JobType.SAMPLE_ML_INGESTION,
        payload={"batch_size": 100},
        idempotency_key="key_123",
    )
    assert valid_submit.job_type == JobType.SAMPLE_ML_INGESTION
    assert valid_submit.idempotency_key == "key_123"

    with pytest.raises(ValidationError):
        JobSubmit(
            job_type="invalid_job_type",  # type: ignore[arg-type]
            payload={},
        )
