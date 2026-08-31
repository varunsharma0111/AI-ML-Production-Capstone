"""Pydantic transport schemas for Dataset Ingestion and Automated Profiling."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    original_filename: str
    storage_path: str
    file_size_bytes: int
    mime_type: str
    format: str
    status: str
    row_count: int | None = None
    column_count: int | None = None
    created_at: datetime
    updated_at: datetime


class DatasetUploadResponse(BaseModel):
    dataset: DatasetResponse
    job_id: UUID | None = None


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    offset: int
    limit: int


class TopValueItem(BaseModel):
    value: str
    count: int


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    min_value: float | int | None = None
    max_value: float | int | None = None
    mean_value: float | None = None
    top_values: list[TopValueItem] | None = None


class DatasetProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    row_count: int
    column_count: int
    columns_json: list[dict[str, Any]]
    created_at: datetime
