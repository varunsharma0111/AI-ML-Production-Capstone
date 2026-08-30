"""Security controls and input sanitization for AI agent tools."""

from __future__ import annotations

import re

from app.core.errors import DomainError


class AgentToolSecurityGuard:
    """Enforces strict path traversal and command injection defenses."""

    DANGEROUS_PATTERNS = [
        re.compile(r"\.\.[/\\]"),  # Path traversal (../ or ..\)
        re.compile(r"[;&|`$><]"),  # Shell injection characters
        re.compile(
            r"^\s*(rm|del|mkfs|chmod|chown)\b", re.IGNORECASE
        ),  # Destructive system commands
    ]

    def validate_input_string(self, value: str, field_name: str = "input") -> str:
        """Validate input string against malicious command injection and path traversal patterns."""
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(value):
                raise DomainError(
                    status_code=400,
                    code="security_violation",
                    detail=(
                        f"Field '{field_name}' contains disallowed characters or unsafe path "
                        "traversal patterns."
                    ),
                )
        return value.strip()
