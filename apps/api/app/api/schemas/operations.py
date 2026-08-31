"""Transport schemas for Operations Dashboard and Audit Event logging."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemMetricsSummary(BaseModel):
    total_datasets: int = 0
    ready_datasets: int = 0
    profiling_datasets: int = 0
    failed_datasets: int = 0

    total_training_jobs: int = 0
    queued_jobs: int = 0
    processing_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0

    total_models: int = 0
    production_models: int = 0
    staging_models: int = 0
    approved_models: int = 0
    rejected_models: int = 0

    total_predictions: int = 0
    average_latency_ms: float = 0.0


class OperationsDashboardResponse(BaseModel):
    system_status: str = "healthy"
    api_status: str = "ok"
    database_status: str = "ok"
    metrics: SystemMetricsSummary


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID
    workspace_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    request_id: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
