"""API tests for workspace-scoped task CRUD, RBAC, isolation, and audit events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.db.models.entities import Task, User, WorkspaceMembership
from app.domains.identity.principal import Principal
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/capstone_test",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
        allowed_jwt_algorithms=("RS256",),
    )


@pytest.fixture
def mock_principal() -> Principal:
    return Principal(
        subject="user_sub_001", email="editor@example.com", display_name="Workspace Editor"
    )


def setup_mock_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    task_repo_get: Task | None = None,
    task_repo_list: list[Task] | None = None,
) -> AsyncMock:
    """Helper to mock DB session queries for task service calls."""

    mock_session = AsyncMock()

    def add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and getattr(obj, "id") is None:
            setattr(obj, "id", uuid4())
        now = datetime.now(UTC)
        if hasattr(obj, "created_at") and getattr(obj, "created_at") is None:
            setattr(obj, "created_at", now)
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at") is None:
            setattr(obj, "updated_at", now)
        table_cols = getattr(getattr(type(obj), "__table__", None), "columns", {})
        if "version" in table_cols and getattr(obj, "version", None) is None:
            setattr(obj, "version", 1)
        if "status" in table_cols and getattr(obj, "status", None) is None:
            setattr(obj, "status", "open")

    mock_session.add = MagicMock(side_effect=add_side_effect)

    # Begin transaction context manager
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    # Populate timestamps on refresh if missing (simulating DB defaults)
    async def refresh_side_effect(obj: Any) -> None:
        add_side_effect(obj)

    mock_session.refresh.side_effect = refresh_side_effect

    # Identity get_or_create_user result
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Identity get_membership result
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership

    # Task get_for_workspace result
    task_get_result = MagicMock()
    task_get_result.scalar_one_or_none.return_value = task_repo_get

    # Task list_for_workspace result
    task_list_result = MagicMock()
    task_list_result.scalars.return_value = task_repo_list or []

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM tasks" in query_str:
            if "OFFSET" in query_str or "LIMIT" in query_str:
                return task_list_result
            return task_get_result
        return MagicMock()

    mock_session.execute.side_effect = execute_side_effect

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)
    app.state.session_factory = mock_session_factory
    return mock_session


@pytest.mark.asyncio
async def test_create_task_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/tasks",
            json={"title": "Test Task"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


@pytest.mark.asyncio
async def test_create_task_unauthorized_non_member(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    setup_mock_db(app, user=user, membership=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/tasks",
            json={"title": "Test Task"},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


@pytest.mark.asyncio
async def test_create_task_forbidden_viewer_role(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )
    setup_mock_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/tasks",
            json={"title": "Test Task"},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


@pytest.mark.asyncio
async def test_create_task_success_editor_role(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    mock_session = setup_mock_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/tasks",
            json={"title": "New Task", "description": "Task description"},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Task"
    assert data["description"] == "Task description"
    assert data["status"] == "open"
    assert data["version"] == 1
    assert data["workspace_id"] == str(workspace_id)
    assert mock_session.add.call_count >= 2  # Task and AuditEvent appended


@pytest.mark.asyncio
async def test_list_tasks_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )
    existing_tasks = [
        Task(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            title="Task 1",
            status="open",
            version=1,
            created_at=now,
            updated_at=now,
        ),
        Task(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            title="Task 2",
            status="completed",
            version=2,
            created_at=now,
            updated_at=now,
        ),
    ]

    setup_mock_db(app, user=user, membership=membership, task_repo_list=existing_tasks)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/tasks?offset=0&limit=10",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["offset"] == 0
    assert data["limit"] == 10
    assert data["items"][0]["title"] == "Task 1"
    assert data["items"][1]["title"] == "Task 2"


@pytest.mark.asyncio
async def test_get_task_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    task_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )
    task = Task(
        id=task_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        title="Single Task",
        description="Detail",
        status="open",
        version=1,
        created_at=now,
        updated_at=now,
    )

    setup_mock_db(app, user=user, membership=membership, task_repo_get=task)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(task_id)
    assert data["title"] == "Single Task"


@pytest.mark.asyncio
async def test_get_task_workspace_isolation_not_found(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_b_id = uuid4()
    task_id = uuid4()

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_b_id, user_id=user.id, role="owner"
    )

    setup_mock_db(app, user=user, membership=membership, task_repo_get=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_b_id}/tasks/{task_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "resource_not_found"


@pytest.mark.asyncio
async def test_update_task_optimistic_concurrency_conflict(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    task_id = uuid4()
    now = datetime.now(UTC)

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="owner"
    )
    existing_task = Task(
        id=task_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        title="Initial Title",
        version=2,
        created_at=now,
        updated_at=now,
    )

    setup_mock_db(app, user=user, membership=membership, task_repo_get=existing_task)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}",
            json={"version": 1, "title": "Conflicting Update"},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "resource_conflict"


@pytest.mark.asyncio
async def test_update_task_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    task_id = uuid4()
    now = datetime.now(UTC)

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="owner"
    )
    existing_task = Task(
        id=task_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        title="Old Title",
        status="open",
        version=1,
        created_at=now,
        updated_at=now,
    )

    mock_session = setup_mock_db(app, user=user, membership=membership, task_repo_get=existing_task)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}",
            json={"version": 1, "title": "Updated Title", "status": "completed"},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "completed"
    assert data["version"] == 2
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_create_task_validation_error(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/tasks",
            json={"title": ""},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_failed"
