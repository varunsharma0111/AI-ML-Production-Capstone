"""Transactional job management service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.jobs import JobSubmit, TrainingJobCreate
from app.core.errors import ConflictError, ResourceNotFoundError
from app.core.redis import RedisManager
from app.db.models.entities import AuditEvent, Job, User
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.jobs import JobRepository
from app.domains.identity.policy import Permission, require_permission
from app.domains.identity.principal import Principal
from app.domains.jobs.types import JobStatus
from services.worker.runner import JobRunner


class JobService:
    def __init__(
        self,
        identity_repository: IdentityRepository | None = None,
        job_repository: JobRepository | None = None,
        job_runner: JobRunner | None = None,
        redis_manager: RedisManager | None = None,
    ) -> None:
        self._identity_repository = identity_repository or IdentityRepository()
        self._job_repository = job_repository or JobRepository()
        self._job_runner = job_runner or JobRunner(self._job_repository)
        self._redis_manager = redis_manager

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
                attempt_count=0,
                version=1,
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

        # Asynchronously enqueue to Redis task queue & publish Pub/Sub notification
        if self._redis_manager:
            await self._redis_manager.enqueue_job("job_queue", str(job.id))
            await self._redis_manager.publish_job_update(
                str(workspace_id),
                {
                    "event": "job_status",
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "workspace_id": str(workspace_id),
                },
            )

        return job

    async def submit_training_job(
        self,
        session: AsyncSession,
        principal: Principal,
        payload: TrainingJobCreate,
        request_id: str,
    ) -> Job:
        async with session.begin():
            user = await self._authorized_user(
                session, principal, payload.workspace_id, Permission.TASK_CREATE
            )

            from app.core.errors import ResourceNotFoundError, ValidationError
            from app.db.repositories.datasets import DatasetRepository
            from app.domains.jobs.types import JobType

            dataset_repo = DatasetRepository()
            dataset = await dataset_repo.get_dataset_for_workspace(
                session, payload.workspace_id, payload.dataset_id
            )
            if dataset is None:
                raise ResourceNotFoundError(f"Dataset {payload.dataset_id} not found in workspace.")

            if dataset.status != "ready":
                raise ValidationError(
                    f"Dataset '{dataset.original_filename}' is not"
                    f" ready for training (status: {dataset.status})."
                )

            profile = await dataset_repo.get_profile_by_dataset_id(session, dataset.id)
            if profile and profile.columns_json:
                col_names = [col["name"] for col in profile.columns_json]
                if payload.target_column not in col_names:
                    raise ValidationError(
                        f"Target column '{payload.target_column}' does not exist in dataset."
                    )

            job_payload = {
                "workspace_id": str(payload.workspace_id),
                "dataset_id": str(payload.dataset_id),
                "target_column": payload.target_column,
                "model_name": payload.model_name,
                "model_type": payload.model_type,
                "hyperparameters": payload.hyperparameters,
            }

            job = Job(
                workspace_id=payload.workspace_id,
                created_by_user_id=user.id,
                job_type=JobType.MODEL_TRAINING.value,
                payload_json=job_payload,
                status=JobStatus.QUEUED.value,
                max_retries=3,
                attempt_count=0,
                version=1,
            )
            await self._job_repository.create_job(session, job)

            audit_event = AuditEvent(
                actor_user_id=user.id,
                workspace_id=payload.workspace_id,
                action="job.submitted",
                resource_type="job",
                resource_id=job.id,
                request_id=request_id,
                metadata_json={"job_type": job.job_type, "model_name": payload.model_name},
            )
            session.add(audit_event)

        # Asynchronously enqueue to Redis task queue & publish Pub/Sub notification
        if self._redis_manager:
            await self._redis_manager.enqueue_job("job_queue", str(job.id))
            await self._redis_manager.publish_job_update(
                str(payload.workspace_id),
                {
                    "event": "job_status",
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "workspace_id": str(payload.workspace_id),
                },
            )

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
        membership = await self._identity_repository.get_membership(
            session, workspace_id, user.id, principal
        )
        if membership is None:
            from app.core.errors import AuthorizationError

            raise AuthorizationError("User is not a member of the specified workspace.")
        require_permission(membership.role, permission)
        return user
