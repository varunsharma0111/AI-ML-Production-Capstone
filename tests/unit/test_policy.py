"""Unit tests for workspace RBAC roles and permissions policy."""

from __future__ import annotations

import pytest

from app.core.errors import AuthorizationError
from app.domains.identity.policy import (
    ROLE_PERMISSIONS,
    Permission,
    WorkspaceRole,
    require_permission,
)


def test_workspace_role_enum_values() -> None:
    assert WorkspaceRole.OWNER == "owner"
    assert WorkspaceRole.EDITOR == "editor"
    assert WorkspaceRole.VIEWER == "viewer"


def test_permission_enum_values() -> None:
    assert Permission.WORKSPACE_READ == "workspace:read"
    assert Permission.TASK_CREATE == "task:create"
    assert Permission.TASK_READ == "task:read"
    assert Permission.TASK_UPDATE == "task:update"


def test_owner_role_has_all_permissions() -> None:
    owner_permissions = ROLE_PERMISSIONS[WorkspaceRole.OWNER]
    assert Permission.WORKSPACE_READ in owner_permissions
    assert Permission.TASK_CREATE in owner_permissions
    assert Permission.TASK_READ in owner_permissions
    assert Permission.TASK_UPDATE in owner_permissions


def test_editor_role_permissions() -> None:
    editor_permissions = ROLE_PERMISSIONS[WorkspaceRole.EDITOR]
    assert Permission.WORKSPACE_READ in editor_permissions
    assert Permission.TASK_CREATE in editor_permissions
    assert Permission.TASK_READ in editor_permissions
    assert Permission.TASK_UPDATE in editor_permissions


def test_viewer_role_permissions() -> None:
    viewer_permissions = ROLE_PERMISSIONS[WorkspaceRole.VIEWER]
    assert Permission.WORKSPACE_READ in viewer_permissions
    assert Permission.TASK_READ in viewer_permissions
    assert Permission.TASK_CREATE not in viewer_permissions
    assert Permission.TASK_UPDATE not in viewer_permissions


def test_require_permission_allows_authorized_actions() -> None:
    require_permission("owner", Permission.TASK_CREATE)
    require_permission("editor", Permission.TASK_CREATE)
    require_permission("editor", Permission.TASK_UPDATE)
    require_permission("viewer", Permission.TASK_READ)


def test_require_permission_blocks_unauthorized_actions() -> None:
    with pytest.raises(AuthorizationError):
        require_permission("viewer", Permission.TASK_CREATE)

    with pytest.raises(AuthorizationError):
        require_permission("viewer", Permission.TASK_UPDATE)


def test_require_permission_blocks_invalid_role() -> None:
    with pytest.raises(AuthorizationError):
        require_permission("invalid_role", Permission.TASK_READ)
