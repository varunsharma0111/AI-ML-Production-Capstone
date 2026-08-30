"""Registered agent tools and strict Pydantic parameter schemas."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    required_permission: str = "task:read"


class CalculatorArgs(BaseModel):
    expression: str = Field(min_length=1, max_length=100)


class WorkspaceSummaryArgs(BaseModel):
    include_completed: bool = Field(default=True)


REGISTERED_TOOLS: dict[str, ToolDefinition] = {
    "calculator": ToolDefinition(
        name="calculator",
        description="Safely evaluates basic arithmetic expressions.",
        required_permission="task:read",
    ),
    "workspace_summary": ToolDefinition(
        name="workspace_summary",
        description="Generates summary metrics for workspace tasks and background jobs.",
        required_permission="task:read",
    ),
}
