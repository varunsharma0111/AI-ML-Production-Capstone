"""Transport schemas for Phase 5, Milestone 3, 4, and 5 ML model management and quality gates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    name: str = Field(min_length=1, max_length=100)
    version_tag: str = Field(min_length=1, max_length=50)
    description: str | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class ModelEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    f1_score: float | None = Field(default=None, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    accuracy_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    f1_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class ModelPromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    target_status: str = Field(pattern="^(staging|production)$")


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    input_features: dict[str, Any]


class QualityGateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: UUID
    workspace_id: UUID | None = None
    status: str
    passed_gate: bool
    accuracy: float
    f1_score: float
    accuracy_threshold: float
    f1_threshold: float
    failure_reasons: list[str]
    evaluated_at: datetime


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version_tag: str
    description: str | None = None
    artifact_path: str
    status: str
    workspace_id: UUID | None = None
    dataset_id: UUID | None = None
    job_id: UUID | None = None
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    hyperparameters_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PredictResponse(BaseModel):
    model_id: UUID
    model_version: str
    prediction: str
    confidence: float
    latency_ms: float


class PredictionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_version_id: UUID
    workspace_id: UUID
    input_features: dict[str, Any]
    prediction: dict[str, Any]
    latency_ms: float
    created_at: datetime
