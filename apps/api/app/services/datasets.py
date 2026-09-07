"""Transactional service for dataset management and automated profiling workflows."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError, ValidationError
from app.core.redis import RedisManager
from app.core.storage import StorageService
from app.db.models.entities import AuditEvent, Dataset, DatasetProfile, Job, User
from app.db.repositories.datasets import DatasetRepository
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.jobs import JobRepository
from app.domains.datasets.types import DatasetStatus
from app.domains.identity.policy import Permission, require_permission
from app.domains.identity.principal import Principal
from app.domains.jobs.types import JobStatus, JobType
from services.worker.runner import JobRunner

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


import asyncio


async def _is_in_transaction(session: AsyncSession) -> bool:
    try:
        res = session.in_transaction()
        if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
            return bool(await res)
        return bool(res)
    except Exception:
        return False


class DatasetService:
    def __init__(
        self,
        identity_repository: IdentityRepository | None = None,
        dataset_repository: DatasetRepository | None = None,
        job_repository: JobRepository | None = None,
        job_runner: JobRunner | None = None,
        storage_service: StorageService | None = None,
        redis_manager: RedisManager | None = None,
    ) -> None:
        self._identity_repository = identity_repository or IdentityRepository()
        self._dataset_repository = dataset_repository or DatasetRepository()
        self._job_repository = job_repository or JobRepository()
        self._job_runner = job_runner or JobRunner(self._job_repository)
        self._storage_service = storage_service or StorageService()
        self._redis_manager = redis_manager

    async def upload_dataset(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        filename: str,
        file_content: bytes,
        content_type: str | None,
        request_id: str,
    ) -> tuple[Dataset, Job]:
        """Validate, store, record, and queue dataset profiling job."""
        if not filename or not filename.strip():
            raise ValidationError("Filename must not be empty.")

        safe_name = Path(filename).name
        if ".." in safe_name or "/" in safe_name or "\\" in safe_name or "\x00" in safe_name:
            raise ValidationError("Filename contains unsafe path traversal characters.")

        if not safe_name.lower().endswith(".csv"):
            raise ValidationError("Only CSV format datasets (.csv) are supported.")

        if content_type and content_type.strip():
            ct = content_type.lower()
            allowed_types = (
                "text/csv",
                "application/csv",
                "text/plain",
                "application/vnd.ms-excel",
                "application/octet-stream",
            )
            if not any(a in ct for a in allowed_types):
                raise ValidationError(f"Unsupported MIME content type: {content_type}")

        file_size = len(file_content)
        if file_size == 0:
            raise ValidationError("Uploaded file is empty.")
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValidationError(f"File size ({file_size} bytes) exceeds maximum limit of {MAX_FILE_SIZE_BYTES} bytes.")

        if await _is_in_transaction(session):
            return await self._upload_dataset_impl(session, principal, workspace_id, safe_name, file_content, content_type, file_size, request_id)
        async with session.begin():
            return await self._upload_dataset_impl(session, principal, workspace_id, safe_name, file_content, content_type, file_size, request_id)

    async def _upload_dataset_impl(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        safe_name: str,
        file_content: bytes,
        content_type: str | None,
        file_size: int,
        request_id: str,
    ) -> tuple[Dataset, Job]:
        user = await self._authorized_user(session, principal, workspace_id, Permission.DATASET_CREATE)

        dataset_id = uuid4()
        storage_path = self._storage_service.save_dataset_file(
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            filename=safe_name,
            content=file_content,
        )

        dataset = Dataset(
            id=dataset_id,
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            original_filename=safe_name,
            storage_path=storage_path,
            file_size_bytes=file_size,
            mime_type=content_type or "text/csv",
            format="csv",
            status=DatasetStatus.UPLOADED.value,
            row_count=None,
            column_count=None,
        )
        await self._dataset_repository.create_dataset(session, dataset)

        job = Job(
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            job_type=JobType.DATASET_PROFILING.value,
            payload_json={
                "dataset_id": str(dataset_id),
                "workspace_id": str(workspace_id),
                "filename": safe_name,
                "request_id": request_id,
            },
            status=JobStatus.QUEUED.value,
            max_retries=3,
            attempt_count=0,
            version=1,
        )
        await self._job_repository.create_job(session, job)

        audit_event = AuditEvent(
            actor_user_id=user.id,
            workspace_id=workspace_id,
            action="dataset.uploaded",
            resource_type="dataset",
            resource_id=dataset.id,
            request_id=request_id,
            metadata_json={"filename": safe_name, "file_size_bytes": file_size},
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

        return dataset, job

    async def list_datasets(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Dataset]:
        """List all datasets in workspace."""
        if await _is_in_transaction(session):
            return await self._list_datasets_impl(session, principal, workspace_id, offset, limit)
        async with session.begin():
            return await self._list_datasets_impl(session, principal, workspace_id, offset, limit)

    async def _list_datasets_impl(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Dataset]:
        await self._authorized_user(session, principal, workspace_id, Permission.DATASET_READ)
        return await self._dataset_repository.list_datasets_for_workspace(session, workspace_id, offset, limit)

    async def get_dataset(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        dataset_id: UUID,
    ) -> Dataset:
        """Retrieve single dataset with workspace isolation."""
        if await _is_in_transaction(session):
            return await self._get_dataset_impl(session, principal, workspace_id, dataset_id)
        async with session.begin():
            return await self._get_dataset_impl(session, principal, workspace_id, dataset_id)

    async def _get_dataset_impl(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        dataset_id: UUID,
    ) -> Dataset:
        await self._authorized_user(session, principal, workspace_id, Permission.DATASET_READ)
        dataset = await self._dataset_repository.get_dataset_for_workspace(session, workspace_id, dataset_id)
        if dataset is None:
            raise ResourceNotFoundError("Dataset not found in workspace.")
        return dataset

    async def get_profile(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        dataset_id: UUID,
    ) -> DatasetProfile:
        """Retrieve profile statistics for dataset with workspace isolation."""
        if await _is_in_transaction(session):
            return await self._get_profile_impl(session, principal, workspace_id, dataset_id)
        async with session.begin():
            return await self._get_profile_impl(session, principal, workspace_id, dataset_id)

    async def _get_profile_impl(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        dataset_id: UUID,
    ) -> DatasetProfile:
        await self._authorized_user(session, principal, workspace_id, Permission.DATASET_READ)
        dataset = await self._dataset_repository.get_dataset_for_workspace(session, workspace_id, dataset_id)
        if dataset is None:
            raise ResourceNotFoundError("Dataset not found in workspace.")

        profile = await self._dataset_repository.get_profile_by_dataset_id(session, dataset_id)
        if profile is None:
            raise ResourceNotFoundError("Profile statistics are not ready for this dataset.")
        return profile

    async def delete_dataset(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        dataset_id: UUID,
        request_id: str = "unknown",
    ) -> None:
        """Delete dataset record and emit audit event."""
        if await _is_in_transaction(session):
            return await self._delete_dataset_impl(session, principal, workspace_id, dataset_id, request_id)
        async with session.begin():
            return await self._delete_dataset_impl(session, principal, workspace_id, dataset_id, request_id)

    async def _delete_dataset_impl(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        dataset_id: UUID,
        request_id: str = "unknown",
    ) -> None:
        user = await self._authorized_user(session, principal, workspace_id, Permission.DATASET_CREATE)
        dataset = await self._dataset_repository.get_dataset_for_workspace(session, workspace_id, dataset_id)
        if dataset is None:
            raise ResourceNotFoundError("Dataset not found in workspace.")

        await self._dataset_repository.delete_dataset(session, dataset)

        session.add(
            AuditEvent(
                actor_user_id=user.id,
                workspace_id=workspace_id,
                action="dataset.deleted",
                resource_type="dataset",
                resource_id=dataset_id,
                request_id=request_id,
                metadata_json={"filename": dataset.original_filename},
            )
        )

    async def _authorized_user(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        permission: Permission,
    ) -> User:
        user = await self._identity_repository.get_or_create_user(session, principal)
        membership = await self._identity_repository.get_membership(session, workspace_id, user.id, principal)
        if membership is None:
            from app.core.errors import AuthorizationError

            raise AuthorizationError("User is not a member of the specified workspace.")
        require_permission(membership.role, permission)
        return user
