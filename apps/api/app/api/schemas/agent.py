"""Transport schemas for Phase 7 and Milestone 5 AI agent tool and orchestrator endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ToolExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    tool_name: str
    result: dict[str, Any]
    duration_ms: float


class ToolSummaryResponse(BaseModel):
    name: str
    description: str
    required_permission: str


class AgentOrchestrateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    message: str = Field(min_length=1, max_length=1000)


class AgentOrchestrateResponse(BaseModel):
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
