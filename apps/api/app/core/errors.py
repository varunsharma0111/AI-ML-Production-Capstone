"""Application errors and client-safe problem responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DomainError(Exception):
    """Expected domain failure with a safe HTTP representation."""

    status_code: int
    code: str
    title: str
    detail: str


class AuthenticationError(DomainError):
    def __init__(self, detail: str = "Authentication credentials are invalid or expired.") -> None:
        super().__init__(401, "authentication_failed", "Unauthorized", detail)


class AuthorizationError(DomainError):
    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(403, "permission_denied", "Forbidden", detail)


class ResourceNotFoundError(DomainError):
    def __init__(self, detail: str = "The requested resource was not found.") -> None:
        super().__init__(404, "resource_not_found", "Not Found", detail)


class ConflictError(DomainError):
    def __init__(self, detail: str = "The resource was modified by another request.") -> None:
        super().__init__(409, "resource_conflict", "Conflict", detail)
