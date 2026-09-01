"""Workspace-scoped protected task routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_request_id,
    get_session,
)
from app.api.schemas.tasks import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.domains.identity.principal import Principal
from app.services.tasks import TaskService

router = APIRouter(prefix="/workspaces/{workspace_id}/tasks", tags=["tasks"])
_task_service = TaskService()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    workspace_id: UUID,
    payload: TaskCreate,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> TaskResponse:
    task = await _task_service.create_task(session, principal, workspace_id, payload, request_id)
    return TaskResponse.model_validate(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    workspace_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> TaskListResponse:
    tasks = await _task_service.list_tasks(session, principal, workspace_id, offset, limit)
    return TaskListResponse(
        items=[TaskResponse.model_validate(task) for task in tasks], offset=offset, limit=limit
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    workspace_id: UUID,
    task_id: UUID,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    task = await _task_service.get_task(session, principal, workspace_id, task_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    workspace_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> TaskResponse:
    task = await _task_service.update_task(
        session, principal, workspace_id, task_id, payload, request_id
    )
    return TaskResponse.model_validate(task)
