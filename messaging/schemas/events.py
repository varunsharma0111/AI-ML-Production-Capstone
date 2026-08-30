"""Versioned JSON event schemas for outbox and Kafka messaging."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    version: int = Field(default=1)
    timestamp: datetime
    payload: dict[str, Any]


class TaskCreatedPayload(BaseModel):
    task_id: UUID
    workspace_id: UUID
    title: str
    created_by_user_id: UUID


class JobSubmittedPayload(BaseModel):
    job_id: UUID
    workspace_id: UUID
    job_type: str
