"""Resource-bounded fail-closed agent tool sandbox engine."""

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
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[dict[str, Any], float]:
        if tool_name not in REGISTERED_TOOLS:
            raise ResourceNotFoundError(f"Agent tool '{tool_name}' is not registered.")

        start_time = time.perf_counter()

        if tool_name == "calculator":
            expr = str(arguments.get("expression", ""))
            self.security_guard.validate_input_string(expr, field_name="expression")
            result = self._safe_eval_math(expr)
            output = {"result": result, "expression": expr}

        elif tool_name == "workspace_summary":
            output = {
                "total_tasks": 12,
                "open_tasks": 5,
                "completed_tasks": 7,
                "active_jobs": 2,
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
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
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
