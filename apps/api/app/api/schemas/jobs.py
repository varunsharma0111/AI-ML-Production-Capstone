"""Transport schemas for Phase 4 job endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.domains.jobs.types import JobStatus, JobType
from pydantic import BaseModel, ConfigDict, Field


class JobSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_type: JobType
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=255)
    max_retries: int = Field(default=3, ge=0, le=10)


class TrainingJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    dataset_id: UUID
    target_column: str = Field(min_length=1, max_length=255)
    model_name: str = Field(min_length=1, max_length=100)
    model_type: str = Field(default="random_forest")
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    idempotency_key: str | None
    job_type: JobType
    payload_json: dict[str, Any]
    status: JobStatus
    result_json: dict[str, Any] | None
    error_detail: str | None
    max_retries: int
    attempt_count: int
    version: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    items: list[JobResponse]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
