"""Scoped job and job-attempt data access repository."""

from __future__ import annotations

from uuid import UUID

from app.db.models.entities import Job, JobAttempt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class JobRepository:
    async def create_job(self, session: AsyncSession, job: Job) -> Job:
        session.add(job)
        await session.flush()
        await session.refresh(job)
        return job

    async def find_by_idempotency_key(
        self, session: AsyncSession, workspace_id: UUID, idempotency_key: str
    ) -> Job | None:
        result = await session.execute(
            select(Job).where(
                Job.workspace_id == workspace_id,
                Job.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, job_id: UUID
    ) -> Job | None:
        result = await session.execute(
            select(Job).where(Job.id == job_id, Job.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, offset: int, limit: int
    ) -> list[Job]:
        result = await session.execute(
            select(Job)
            .where(Job.workspace_id == workspace_id)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars())

    async def record_attempt(self, session: AsyncSession, attempt: JobAttempt) -> None:
        session.add(attempt)
        await session.flush()
