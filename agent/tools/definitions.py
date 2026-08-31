"""Registered agent tools and strict Pydantic parameter schemas for ML platform analytics."""

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


class CompareModelsArgs(BaseModel):
    model_name_1: str = Field(..., description="First model name or version tag")
    model_name_2: str = Field(..., description="Second model name or version tag")


class ExplainMetricsArgs(BaseModel):
    model_id_or_name: str = Field(..., description="Model ID, name, or version tag")


class SummarizeDatasetArgs(BaseModel):
    dataset_id_or_name: str = Field(..., description="Dataset ID or original filename")


class AgentPredictArgs(BaseModel):
    model_id_or_name: str = Field(..., description="Model ID, name, or version tag")
    input_features: dict[str, Any] = Field(..., description="Key-value input feature dictionary")


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
    "list_models": ToolDefinition(
        name="list_models",
        description="Lists all versioned ML models belonging to the active workspace.",
        required_permission="model:read",
    ),
    "list_datasets": ToolDefinition(
        name="list_datasets",
        description="Lists all uploaded CSV datasets in the active workspace.",
        required_permission="dataset:read",
    ),
    "compare_models": ToolDefinition(
        name="compare_models",
        description=(
            "Compares performance metrics, training datasets, "
            "hyperparameters, and lifecycle status of two model versions."
        ),
        required_permission="model:read",
    ),
    "explain_metrics": ToolDefinition(
        name="explain_metrics",
        description=(
            "Explains Quality Gate evaluation metrics, "
            "threshold pass/fail criteria, and failure reasons "
            "for a model version."
        ),
        required_permission="model:read",
    ),
    "summarize_dataset": ToolDefinition(
        name="summarize_dataset",
        description=(
            "Summarizes dataset profiling statistics, column types, "
            "row counts, missing value percentages, "
            "and categorical distributions."
        ),
        required_permission="dataset:read",
    ),
    "run_prediction": ToolDefinition(
        name="run_prediction",
        description="Executes real-time model inference using the platform's controlled inference engine.",
        required_permission="model:read",
    ),
}
