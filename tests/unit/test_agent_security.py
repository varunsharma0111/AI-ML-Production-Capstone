"""Unit tests for Phase 7 agent tool security guards and sandbox execution."""

from __future__ import annotations

import pytest

from agent.tools.sandbox import ToolSandbox
from agent.tools.security import AgentToolSecurityGuard
from app.core.errors import DomainError, ResourceNotFoundError


def test_path_traversal_rejection() -> None:
    guard = AgentToolSecurityGuard()
    with pytest.raises(DomainError) as exc_info:
        guard.validate_input_string("../../../etc/passwd", field_name="file_path")

    assert exc_info.value.code == "security_violation"


def test_command_injection_rejection() -> None:
    guard = AgentToolSecurityGuard()
    with pytest.raises(DomainError) as exc_info:
        guard.validate_input_string("1 + 1; rm -rf /", field_name="expression")

    assert exc_info.value.code == "security_violation"


def test_sandbox_calculator_execution() -> None:
    sandbox = ToolSandbox()
    output, duration = sandbox.execute_tool("calculator", {"expression": "10 + 20 * 2"})
    assert output["result"] == 50.0
    assert duration >= 0.0


def test_sandbox_unregistered_tool_fails() -> None:
    sandbox = ToolSandbox()
    with pytest.raises(ResourceNotFoundError):
        sandbox.execute_tool("unknown_tool", {})
