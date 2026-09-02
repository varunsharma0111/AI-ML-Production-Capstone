"""Background job execution engine and retry processor."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import Job, JobAttempt
from app.db.repositories.jobs import JobRepository
from app.domains.jobs.types import JobStatus, JobType

logger = logging.getLogger(__name__)


class JobRunner:
    """Executes asynchronous background jobs with retries and attempt logging."""

    def __init__(self, job_repository: JobRepository | None = None) -> None:
        self._job_repository = job_repository or JobRepository()

    async def recover_stuck_jobs(self, session: AsyncSession, max_stuck_minutes: int = 15) -> int:
        """Find jobs stuck in PROCESSING longer than max_stuck_minutes and requeue or fail them."""
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(minutes=max_stuck_minutes)
        stuck_jobs = await self._job_repository.get_stuck_processing_jobs(session, cutoff)
        recovered_count = 0
        for job in stuck_jobs:
            if (job.attempt_count or 0) < job.max_retries:
                job.status = JobStatus.QUEUED.value
                logger.warning(
                    "Requeueing stuck job %s (attempt %d/%d)",
                    job.id,
                    job.attempt_count or 0,
                    job.max_retries,
                )
            else:
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.now(UTC)
                logger.error("Marking stuck job %s FAILED after exceeding max retries", job.id)
            recovered_count += 1
        if recovered_count > 0:
            await session.commit()
        return recovered_count

    async def execute_job(
        self, session: AsyncSession, job: Job
    ) -> tuple[JobStatus, dict[str, Any] | None, str | None]:
        """Run simulated job execution based on job type."""
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        job.status = JobStatus.PROCESSING.value
        if job.attempt_count is None or job.attempt_count == 0:
            job.attempt_count = 1
        await session.flush()

        start_time = datetime.now(UTC)
        attempt_number = job.attempt_count

        try:
            req_id = (
                str(job.payload_json.get("request_id", "unknown"))
                if isinstance(job.payload_json, dict)
                else "unknown"
            )
            ws_id = str(job.workspace_id)
            logger.info(
                "Executing job %s (type=%s, attempt=%d)",
                job.id,
                job.job_type,
                attempt_number,
                extra={"request_id": req_id, "job_id": str(job.id), "workspace_id": ws_id},
            )

            result: dict[str, Any] = {}
            if job.job_type == JobType.SAMPLE_ML_INGESTION.value:
                result = {
                    "records_processed": 1250,
                    "dataset_version": "v1.2.0",
                    "status": "ingested",
                }
            elif job.job_type == JobType.DATA_EXPORT.value:
                result = {
                    "export_url": "s3://exports/data_export_2026.csv",
                    "format": "csv",
                    "bytes": 45890,
                }
            elif job.job_type == JobType.DATASET_PROFILING.value:
                from uuid import UUID

                from app.db.models.entities import AuditEvent, DatasetProfile
                from app.db.repositories.datasets import DatasetRepository
                from app.domains.datasets.types import DatasetStatus
                from app.services.profiler import profile_csv_file

                dataset_repo = DatasetRepository()
                dataset_id = UUID(str(job.payload_json["dataset_id"]))
                dataset = await dataset_repo.get_dataset(session, dataset_id)
                if dataset is None:
                    raise ValueError(f"Dataset {dataset_id} not found for profiling job.")

                dataset.status = DatasetStatus.PROFILING.value
                await session.flush()

                audit_event_start = AuditEvent(
                    actor_user_id=dataset.created_by_user_id,
                    workspace_id=dataset.workspace_id,
                    action="dataset.profiling_started",
                    resource_type="dataset",
                    resource_id=dataset.id,
                    request_id=str(job.id),
                    metadata_json={"filename": dataset.original_filename},
                )
                session.add(audit_event_start)

                row_count, col_count, columns_stats = profile_csv_file(dataset.storage_path)

                profile = DatasetProfile(
                    dataset_id=dataset.id,
                    row_count=row_count,
                    column_count=col_count,
                    columns_json=columns_stats,
                )
                await dataset_repo.create_profile(session, profile)

                dataset.status = DatasetStatus.READY.value
                dataset.row_count = row_count
                dataset.column_count = col_count
                await session.flush()

                audit_event_done = AuditEvent(
                    actor_user_id=dataset.created_by_user_id,
                    workspace_id=dataset.workspace_id,
                    action="dataset.profiling_completed",
                    resource_type="dataset",
                    resource_id=dataset.id,
                    request_id=str(job.id),
                    metadata_json={
                        "filename": dataset.original_filename,
                        "row_count": row_count,
                        "column_count": col_count,
                    },
                )
                session.add(audit_event_done)

                result = {
                    "dataset_id": str(dataset.id),
                    "row_count": row_count,
                    "column_count": col_count,
                    "status": "ready",
                }
            elif job.job_type == JobType.MODEL_TRAINING.value:
                from uuid import UUID

                from app.db.models.entities import AuditEvent, ModelVersion
                from app.db.repositories.datasets import DatasetRepository
                from ml.training.trainer import ModelTrainer

                dataset_repo = DatasetRepository()
                dataset_id = UUID(str(job.payload_json["dataset_id"]))
                workspace_id = UUID(str(job.payload_json["workspace_id"]))
                target_column = str(job.payload_json["target_column"])
                model_name = str(job.payload_json["model_name"])
                model_type = str(job.payload_json.get("model_type", "random_forest"))
                raw_params = (
                    job.payload_json.get("hyperparameters")
                    if isinstance(job.payload_json, dict)
                    else {}
                )
                hyperparameters = dict(raw_params) if isinstance(raw_params, dict) else {}
                version_tag = str(
                    job.payload_json.get(
                        "version_tag", f"v1.{str(job.id)[:6]}.{job.attempt_count}"
                    )
                )

                dataset = await dataset_repo.get_dataset(session, dataset_id)
                if dataset is None or dataset.status != "ready":
                    raise ValueError(f"Dataset {dataset_id} is not ready for model training.")

                audit_event_start = AuditEvent(
                    actor_user_id=job.created_by_user_id,
                    workspace_id=workspace_id,
                    action="training.started",
                    resource_type="job",
                    resource_id=job.id,
                    request_id=str(job.id),
                    metadata_json={
                        "dataset_id": str(dataset.id),
                        "target_column": target_column,
                        "model_name": model_name,
                        "model_type": model_type,
                    },
                )
                session.add(audit_event_start)

                trainer = ModelTrainer()
                metrics, artifact_path = trainer.train_dataset_model(
                    csv_file_path=dataset.storage_path,
                    target_column=target_column,
                    model_name=model_name,
                    version_tag=version_tag,
                    model_type=model_type,
                    hyperparameters=hyperparameters,
                    workspace_id=workspace_id,
                )

                model_version = ModelVersion(
                    name=model_name,
                    version_tag=version_tag,
                    description=f"Trained on {dataset.original_filename} (target: {target_column})",
                    artifact_path=artifact_path,
                    status="draft",
                    workspace_id=workspace_id,
                    dataset_id=dataset.id,
                    job_id=job.id,
                    metrics_json=metrics,
                    hyperparameters_json=hyperparameters,
                )
                session.add(model_version)
                await session.flush()

                audit_event_done = AuditEvent(
                    actor_user_id=job.created_by_user_id,
                    workspace_id=workspace_id,
                    action="training.completed",
                    resource_type="job",
                    resource_id=job.id,
                    request_id=str(job.id),
                    metadata_json={
                        "model_version_id": str(model_version.id),
                        "metrics": metrics,
                    },
                )
                session.add(audit_event_done)

                audit_event_reg = AuditEvent(
                    actor_user_id=job.created_by_user_id,
                    workspace_id=workspace_id,
                    action="model.registered",
                    resource_type="model_version",
                    resource_id=model_version.id,
                    request_id=str(job.id),
                    metadata_json={
                        "version_tag": version_tag,
                        "artifact_path": artifact_path,
                    },
                )
                session.add(audit_event_reg)

                result = {
                    "model_version_id": str(model_version.id),
                    "version_tag": version_tag,
                    "artifact_path": artifact_path,
                    "metrics": metrics,
                    "model_name": model_name,
                    "model_type": model_type,
                    "target_column": target_column,
                }
            else:
                result = {"processed": True, "payload": job.payload_json}

            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Record successful attempt
            attempt = JobAttempt(
                job_id=job.id,
                attempt_number=attempt_number,
                status=JobStatus.COMPLETED.value,
                duration_ms=duration_ms,
            )
            await self._job_repository.record_attempt(session, attempt)

            job.status = JobStatus.COMPLETED.value
            job.result_json = result
            job.completed_at = datetime.now(UTC)
            await session.flush()

            return JobStatus.COMPLETED, result, None

        except Exception as exc:
            await session.rollback()
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error_str = str(exc) or "Job processing failed."
            logger.exception("Job %s failed during execution: %s", job.id, exc)

            if job.job_type == JobType.DATASET_PROFILING.value and "dataset_id" in job.payload_json:
                try:
                    from uuid import UUID

                    from app.db.models.entities import AuditEvent
                    from app.db.repositories.datasets import DatasetRepository
                    from app.domains.datasets.types import DatasetStatus

                    dataset_repo = DatasetRepository()
                    ds_id = UUID(str(job.payload_json["dataset_id"]))
                    ds = await dataset_repo.get_dataset(session, ds_id)
                    if ds is not None:
                        ds.status = DatasetStatus.FAILED.value
                        audit_event_fail = AuditEvent(
                            actor_user_id=ds.created_by_user_id,
                            workspace_id=ds.workspace_id,
                            action="dataset.profiling_failed",
                            resource_type="dataset",
                            resource_id=ds.id,
                            request_id=str(job.id),
                            metadata_json={"error": error_str},
                        )
                        session.add(audit_event_fail)
                except Exception:
                    pass
            if job.job_type == JobType.MODEL_TRAINING.value:
                try:
                    from uuid import UUID

                    from app.db.models.entities import AuditEvent

                    ws_uuid = UUID(str(job.payload_json.get("workspace_id")))
                    audit_event_fail = AuditEvent(
                        actor_user_id=job.created_by_user_id,
                        workspace_id=ws_uuid,
                        action="training.failed",
                        resource_type="job",
                        resource_id=job.id,
                        request_id=str(job.id),
                        metadata_json={"error": error_str},
                    )
                    session.add(audit_event_fail)
                except Exception:
                    pass

            attempt = JobAttempt(
                job_id=job.id,
                attempt_number=attempt_number,
                status=JobStatus.FAILED.value,
                error_detail=error_str,
                duration_ms=duration_ms,
            )
            await self._job_repository.record_attempt(session, attempt)

            if job.attempt_count < job.max_retries:
                job.status = JobStatus.QUEUED.value
                logger.warning(
                    "Job %s failed (attempt %d/%d). Re-queueing for retry.",
                    job.id,
                    job.attempt_count,
                    job.max_retries,
                )
            else:
                job.status = JobStatus.FAILED.value
                job.error_detail = error_str
                job.completed_at = datetime.now(UTC)
                logger.error(
                    "Job %s permanently failed after %d attempts.", job.id, job.max_retries
                )

            await session.flush()
            return JobStatus(job.status), None, error_str
