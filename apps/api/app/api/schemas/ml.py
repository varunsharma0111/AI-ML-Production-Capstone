"""Transport schemas for Phase 5 ML model management and controlled inference."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.domains.ml.types import ModelStatus
from pydantic import BaseModel, ConfigDict, Field


class ModelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    version_tag: str = Field(min_length=1, max_length=50)
    description: str | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class ModelEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accuracy: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    input_features: dict[str, Any]


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version_tag: str
    description: str | None
    artifact_path: str
    status: ModelStatus
    created_at: datetime
    updated_at: datetime


class PredictResponse(BaseModel):
    model_version_id: UUID
    prediction: dict[str, Any]
    latency_ms: float
