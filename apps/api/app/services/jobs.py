"""Transactional job management service."""

from __future__ import annotations

from uuid import UUID

from app.api.schemas.jobs import JobSubmit
from app.core.errors import ConflictError, ResourceNotFoundError
from app.db.models.entities import AuditEvent, Job, User
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.jobs import JobRepository
from app.domains.identity.policy import Permission, require_permission
from app.domains.identity.principal import Principal
from app.domains.jobs.types import JobStatus
from sqlalchemy.ext.asyncio import AsyncSession

from services.worker.runner import JobRunner


class JobService:
    def __init__(
        self,
        identity_repository: IdentityRepository | None = None,
        job_repository: JobRepository | None = None,
        job_runner: JobRunner | None = None,
    ) -> None:
        self._identity_repository = identity_repository or IdentityRepository()
        self._job_repository = job_repository or JobRepository()
        self._job_runner = job_runner or JobRunner(self._job_repository)

    async def submit_job(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        payload: JobSubmit,
        request_id: str,
    ) -> Job:
        async with session.begin():
            user = await self._authorized_user(
                session, principal, workspace_id, Permission.TASK_CREATE
            )

            # Idempotency check
            if payload.idempotency_key:
                existing_job = await self._job_repository.find_by_idempotency_key(
                    session, workspace_id, payload.idempotency_key
                )
                if existing_job is not None:
                    return existing_job

            job = Job(
                workspace_id=workspace_id,
                created_by_user_id=user.id,
                idempotency_key=payload.idempotency_key,
                job_type=payload.job_type.value,
                payload_json=payload.payload,
                status=JobStatus.QUEUED.value,
                max_retries=payload.max_retries,
            )
            await self._job_repository.create_job(session, job)

            audit_event = AuditEvent(
                actor_user_id=user.id,
                workspace_id=workspace_id,
                action="job.submitted",
                resource_type="job",
                resource_id=job.id,
                request_id=request_id,
                metadata_json={"job_type": job.job_type},
            )
            session.add(audit_event)

        # Run background job execution inline for immediate local execution & verification
        async with session.begin():
            await self._job_runner.execute_job(session, job)

        return job

    async def list_jobs(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Job]:
        async with session.begin():
            await self._authorized_user(session, principal, workspace_id, Permission.TASK_READ)
            return await self._job_repository.list_for_workspace(
                session, workspace_id, offset, limit
            )

    async def get_job(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        job_id: UUID,
    ) -> Job:
        async with session.begin():
            await self._authorized_user(session, principal, workspace_id, Permission.TASK_READ)
            job = await self._job_repository.get_for_workspace(session, workspace_id, job_id)
            if job is None:
                raise ResourceNotFoundError("Job not found in workspace.")
            return job

    async def cancel_job(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        job_id: UUID,
        request_id: str,
    ) -> Job:
        async with session.begin():
            user = await self._authorized_user(
                session, principal, workspace_id, Permission.TASK_UPDATE
            )
            job = await self._job_repository.get_for_workspace(session, workspace_id, job_id)
            if job is None:
                raise ResourceNotFoundError("Job not found in workspace.")

            if job.status in (
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
            ):
                raise ConflictError(f"Cannot cancel job in state {job.status}.")

            job.status = JobStatus.CANCELLED.value
            job.version += 1
            await session.flush()

            audit_event = AuditEvent(
                actor_user_id=user.id,
                workspace_id=workspace_id,
                action="job.cancelled",
                resource_type="job",
                resource_id=job.id,
                request_id=request_id,
                metadata_json={"previous_status": job.status},
            )
            session.add(audit_event)
            return job

    async def _authorized_user(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        permission: Permission,
    ) -> User:
        user = await self._identity_repository.get_or_create_user(session, principal)
        membership = await self._identity_repository.get_membership(session, workspace_id, user.id)
        if membership is None:
            from app.core.errors import AuthorizationError

            raise AuthorizationError("You are not a member of this workspace.")
        require_permission(membership.role, permission)
        return user
