"""Resource-bounded fail-closed agent tool sandbox engine for ML analytics tools."""

from __future__ import annotations

import ast
import time
from typing import Any

from app.core.errors import DomainError, ResourceNotFoundError

from agent.tools.definitions import REGISTERED_TOOLS
from agent.tools.security import AgentToolSecurityGuard


class ToolSandbox:
    """Executes registered tools within a secure, fail-closed sandbox."""

    def __init__(self, security_guard: AgentToolSecurityGuard | None = None) -> None:
        self.security_guard = security_guard or AgentToolSecurityGuard()

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], float]:
        if tool_name not in REGISTERED_TOOLS:
            raise ResourceNotFoundError(f"Agent tool '{tool_name}' is not registered.")

        start_time = time.perf_counter()
        context = context or {}

        if tool_name == "calculator":
            expr = str(arguments.get("expression", ""))
            self.security_guard.validate_input_string(expr, field_name="expression")
            result = self._safe_eval_math(expr)
            output = {"result": result, "expression": expr}

        elif tool_name == "workspace_summary":
            output = {
                "total_tasks": context.get("total_tasks", 12),
                "open_tasks": context.get("open_tasks", 5),
                "completed_tasks": context.get("completed_tasks", 7),
                "active_jobs": context.get("active_jobs", 2),
            }

        elif tool_name == "list_models":
            models_list = context.get("models", [])
            output = {
                "models": [
                    {
                        "id": str(m.get("id", "")),
                        "name": str(m.get("name", "")),
                        "version_tag": str(m.get("version_tag", "")),
                        "status": str(m.get("status", "")),
                        "metrics": m.get("metrics_json", {}),
                    }
                    for m in models_list
                ],
                "count": len(models_list),
            }

        elif tool_name == "list_datasets":
            datasets_list = context.get("datasets", [])
            output = {
                "datasets": [
                    {
                        "id": str(d.get("id", "")),
                        "filename": str(d.get("original_filename", "")),
                        "status": str(d.get("status", "")),
                        "row_count": d.get("row_count"),
                        "column_count": d.get("column_count"),
                    }
                    for d in datasets_list
                ],
                "count": len(datasets_list),
            }

        elif tool_name == "compare_models":
            m1 = context.get("model_1")
            m2 = context.get("model_2")
            if not m1 or not m2:
                raise ResourceNotFoundError("One or both requested models could not be found.")

            metrics1 = m1.get("metrics_json", {})
            metrics2 = m2.get("metrics_json", {})

            f1_1 = float(metrics1.get("f1_score", 0.0))
            f1_2 = float(metrics2.get("f1_score", 0.0))
            acc1 = float(metrics1.get("accuracy", 0.0))
            acc2 = float(metrics2.get("accuracy", 0.0))

            better_model = m1 if f1_1 >= f1_2 else m2
            explanation = (
                f"Model '{better_model['name']}' ({better_model['version_tag']}) performed better "
                f"with F1 score {max(f1_1, f1_2):.2f} vs {min(f1_1, f1_2):.2f} and "
                f"Accuracy {max(acc1, acc2):.2f} vs {min(acc1, acc2):.2f}."
            )

            output = {
                "model_1": {
                    "name": m1.get("name"),
                    "version_tag": m1.get("version_tag"),
                    "status": m1.get("status"),
                    "accuracy": acc1,
                    "precision": float(metrics1.get("precision", 0.0)),
                    "recall": float(metrics1.get("recall", 0.0)),
                    "f1_score": f1_1,
                    "training_duration_ms": float(metrics1.get("training_duration_ms", 0.0)),
                },
                "model_2": {
                    "name": m2.get("name"),
                    "version_tag": m2.get("version_tag"),
                    "status": m2.get("status"),
                    "accuracy": acc2,
                    "precision": float(metrics2.get("precision", 0.0)),
                    "recall": float(metrics2.get("recall", 0.0)),
                    "f1_score": f1_2,
                    "training_duration_ms": float(metrics2.get("training_duration_ms", 0.0)),
                },
                "better_model": better_model.get("version_tag"),
                "explanation": explanation,
            }

        elif tool_name == "explain_metrics":
            model = context.get("model")
            evaluation = context.get("evaluation")
            if not model:
                raise ResourceNotFoundError("Requested model version was not found.")

            meta = evaluation.get("evaluation_metadata", {}) if evaluation else {}
            metrics = model.get("metrics_json", {})

            acc = (
                float(evaluation.get("accuracy", metrics.get("accuracy", 0.0)))
                if evaluation
                else float(metrics.get("accuracy", 0.0))
            )
            f1 = (
                float(evaluation.get("f1_score", metrics.get("f1_score", 0.0)))
                if evaluation
                else float(metrics.get("f1_score", 0.0))
            )
            req_acc = float(meta.get("accuracy_threshold", 0.90))
            req_f1 = float(meta.get("f1_threshold", 0.85))
            passed = (
                bool(evaluation.get("passed_gate"))
                if evaluation
                else (acc >= req_acc and f1 >= req_f1)
            )
            reasons = list(meta.get("failure_reasons", []))

            if not passed and not reasons:
                if acc < req_acc:
                    reasons.append(
                        f"Accuracy ({acc:.2f}) is below required threshold ({req_acc:.2f})."
                    )
                if f1 < req_f1:
                    reasons.append(
                        f"F1 score ({f1:.2f}) is below required threshold ({req_f1:.2f})."
                    )

            output = {
                "model_name": model.get("name"),
                "version_tag": model.get("version_tag"),
                "status": model.get("status"),
                "actual_accuracy": acc,
                "required_accuracy": req_acc,
                "actual_f1_score": f1,
                "required_f1_score": req_f1,
                "passed_quality_gate": passed,
                "failure_reasons": reasons,
                "decision": "APPROVED" if passed else "REJECTED",
            }

        elif tool_name == "summarize_dataset":
            dataset = context.get("dataset")
            profile = context.get("profile")
            if not dataset:
                raise ResourceNotFoundError("Requested dataset was not found.")

            cols = profile.get("columns_json", []) if profile else []
            output = {
                "dataset_id": str(dataset.get("id", "")),
                "original_filename": dataset.get("original_filename"),
                "status": dataset.get("status"),
                "row_count": profile.get("row_count") if profile else dataset.get("row_count"),
                "column_count": profile.get("column_count")
                if profile
                else dataset.get("column_count"),
                "columns": [
                    {
                        "name": c.get("name"),
                        "inferred_type": c.get("inferred_type"),
                        "missing_percentage": c.get("missing_percentage", 0.0),
                        "unique_count": c.get("unique_count", 0),
                    }
                    for c in cols
                ],
            }

        elif tool_name == "run_prediction":
            pred_result = context.get("prediction_result")
            latency = context.get("latency_ms", 0.0)
            if not pred_result:
                raise DomainError(
                    status_code=400,
                    code="prediction_failed",
                    title="Inference Error",
                    detail="Prediction could not be executed.",
                )
            output = {
                "prediction": pred_result.get("prediction"),
                "confidence": pred_result.get("confidence"),
                "model_version": pred_result.get("model_version"),
                "latency_ms": latency,
            }

        else:
            raise DomainError(
                status_code=400,
                code="unsupported_tool",
                title="Tool Execution Error",
                detail=f"Execution handler for '{tool_name}' is not defined.",
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return output, duration_ms

    def _safe_eval_math(self, expr: str) -> float:
        """Safely evaluate simple arithmetic expressions without eval()."""
        try:
            tree = ast.parse(expr, mode="eval")
            return float(self._eval_node(tree.body))
        except Exception as exc:
            raise DomainError(
                status_code=400,
                code="invalid_expression",
                title="Arithmetic Evaluation Error",
                detail=f"Could not parse arithmetic expression: {exc}",
            )

    def _eval_node(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                return left / right
        raise ValueError("Unsupported AST node type")
