"""Transport schemas for Phase 2 task endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domains.tasks.types import TaskStatus

TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
TaskDescription = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)
]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle
    description: TaskDescription | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    title: TaskTitle | None = None
    description: TaskDescription | None = None
    status: TaskStatus | None = None

    @model_validator(mode="after")
    def require_update(self) -> TaskUpdate:
        if self.title is None and self.description is None and self.status is None:
            raise ValueError("At least one mutable task field must be supplied.")
        return self


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    version: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
