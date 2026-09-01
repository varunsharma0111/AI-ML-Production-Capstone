"""Scoped job and job-attempt data access repository."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import Job, JobAttempt


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

    async def get_job_by_id(self, session: AsyncSession, job_id: UUID) -> Job | None:
        result = await session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_next_queued_job(self, session: AsyncSession) -> Job | None:
        result = await session.execute(
            select(Job)
            .where(Job.status == "queued")
            .order_by(Job.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return result.scalar_one_or_none()

    async def get_stuck_processing_jobs(
        self, session: AsyncSession, cutoff_datetime: Any
    ) -> list[Job]:
        result = await session.execute(
            select(Job).where(
                Job.status == "processing",
                Job.started_at < cutoff_datetime,
            )
        )
        return list(result.scalars())
