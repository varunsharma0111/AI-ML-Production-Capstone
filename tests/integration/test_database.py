"""Integration tests for identity and task database repositories."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.db.models.entities import AuditEvent, Task, User, WorkspaceMembership
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.tasks import TaskRepository
from app.domains.identity.principal import Principal


@pytest.mark.asyncio
async def test_identity_repository_get_or_create_user_existing() -> None:
    repo = IdentityRepository()
    principal = Principal(subject="sub_123", email="user@example.com", display_name="Test User")

    existing_user = User(
        id=uuid4(),
        oidc_subject=principal.subject,
        email=principal.email,
        display_name=principal.display_name,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    user = await repo.get_or_create_user(mock_session, principal)

    assert user.id == existing_user.id
    assert user.oidc_subject == "sub_123"
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_identity_repository_get_or_create_user_new() -> None:
    repo = IdentityRepository()
    principal = Principal(subject="sub_456", email="new@example.com", display_name="New User")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    user = await repo.get_or_create_user(mock_session, principal)

    assert user.oidc_subject == "sub_456"
    assert user.email == "new@example.com"
    assert user.display_name == "New User"
    mock_session.add.assert_called_once_with(user)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_identity_repository_get_membership_found() -> None:
    repo = IdentityRepository()
    workspace_id = uuid4()
    user_id = uuid4()

    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user_id, role="editor"
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = membership

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    result = await repo.get_membership(mock_session, workspace_id, user_id)

    assert result is not None
    assert result.role == "editor"
    assert result.workspace_id == workspace_id


@pytest.mark.asyncio
async def test_identity_repository_get_membership_not_found() -> None:
    repo = IdentityRepository()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    result = await repo.get_membership(mock_session, uuid4(), uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_task_repository_create() -> None:
    repo = TaskRepository()
    task = Task(
        workspace_id=uuid4(),
        created_by_user_id=uuid4(),
        title="Sample Task",
        description="Sample Description",
    )

    mock_session = AsyncMock()

    result = await repo.create(mock_session, task)

    assert result.title == "Sample Task"
    mock_session.add.assert_called_once_with(task)
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(task)


@pytest.mark.asyncio
async def test_task_repository_list_for_workspace() -> None:
    repo = TaskRepository()
    workspace_id = uuid4()
    tasks = [
        Task(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=uuid4(),
            title="Task 1",
        ),
        Task(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=uuid4(),
            title="Task 2",
        ),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value = tasks

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    items = await repo.list_for_workspace(mock_session, workspace_id, offset=0, limit=10)

    assert len(items) == 2
    assert items[0].title == "Task 1"
    assert items[1].title == "Task 2"


@pytest.mark.asyncio
async def test_task_repository_get_for_workspace() -> None:
    repo = TaskRepository()
    workspace_id = uuid4()
    task_id = uuid4()
    expected_task = Task(
        id=task_id,
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        title="Task Detail",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_task

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    result = await repo.get_for_workspace(mock_session, workspace_id, task_id)

    assert result is not None
    assert result.id == task_id
    assert result.title == "Task Detail"


@pytest.mark.asyncio
async def test_task_repository_append_audit_event() -> None:
    repo = TaskRepository()
    event = AuditEvent(
        actor_user_id=uuid4(),
        workspace_id=uuid4(),
        action="task.created",
        resource_type="task",
        resource_id=uuid4(),
        request_id="req_test_123",
        metadata_json={"task_version": 1},
    )

    mock_session = AsyncMock()

    await repo.append_audit_event(mock_session, event)

    mock_session.add.assert_called_once_with(event)
    mock_session.flush.assert_awaited_once()
