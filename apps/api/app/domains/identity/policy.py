"""Phase 2 workspace roles and permission mapping."""

from __future__ import annotations

from enum import StrEnum

from app.core.errors import AuthorizationError


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(StrEnum):
    WORKSPACE_READ = "workspace:read"
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),
    WorkspaceRole.EDITOR: frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_UPDATE,
        }
    ),
    WorkspaceRole.VIEWER: frozenset({Permission.WORKSPACE_READ, Permission.TASK_READ}),
}


def require_permission(role: str, permission: Permission) -> None:
    """Fail closed when a membership role cannot perform an action."""

    try:
        resolved_role = WorkspaceRole(role)
    except ValueError as error:
        raise AuthorizationError() from error
    if permission not in ROLE_PERMISSIONS[resolved_role]:
        raise AuthorizationError()
