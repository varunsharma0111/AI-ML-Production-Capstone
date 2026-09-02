"""Phase 2 workspace roles and permission mapping."""

from __future__ import annotations

from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(StrEnum):
    WORKSPACE_READ = "workspace:read"
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    DATASET_CREATE = "dataset:create"
    DATASET_READ = "dataset:read"
    MODEL_EVALUATE = "model:evaluate"
    MODEL_PROMOTE = "model:promote"
    MODEL_READ = "model:read"
    MODEL_TRAIN = "model:train"
    WORKSPACE_DELETE = "workspace:delete"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),
    WorkspaceRole.EDITOR: frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_UPDATE,
            Permission.DATASET_CREATE,
            Permission.DATASET_READ,
            Permission.MODEL_EVALUATE,
            Permission.MODEL_PROMOTE,
            Permission.MODEL_READ,
            Permission.MODEL_TRAIN,
        }
    ),
    WorkspaceRole.VIEWER: frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.TASK_READ,
            Permission.DATASET_READ,
            Permission.MODEL_READ,
        }
    ),
}


def require_permission(role: str, permission: Permission) -> None:
    """Enforce role permissions based on WorkspaceRole and Permission mapping."""
    try:
        ws_role = WorkspaceRole(role.lower())
    except ValueError:
        from app.core.errors import AuthorizationError

        raise AuthorizationError(f"Invalid workspace role: {role}")

    allowed_perms = ROLE_PERMISSIONS.get(ws_role, frozenset())
    if permission not in allowed_perms:
        from app.core.errors import AuthorizationError

        raise AuthorizationError(
            f"Role '{role}' does not have required permission '{permission.value}'"
        )
