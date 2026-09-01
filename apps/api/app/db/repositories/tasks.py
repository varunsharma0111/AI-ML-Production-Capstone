"""Scoped task and audit-event data access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import AuditEvent, Task


class TaskRepository:
    async def create(self, session: AsyncSession, task: Task) -> Task:
        session.add(task)
        await session.flush()
        await session.refresh(task)
        return task

    async def list_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, offset: int, limit: int
    ) -> list[Task]:
        result = await session.execute(
            select(Task)
            .where(Task.workspace_id == workspace_id)
            .order_by(Task.created_at.desc(), Task.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars())

    async def get_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, task_id: UUID
    ) -> Task | None:
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def append_audit_event(self, session: AsyncSession, event: AuditEvent) -> None:
        session.add(event)
        await session.flush()
