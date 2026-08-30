"""Background job execution engine and retry processor."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

from app.db.models.entities import Job, JobAttempt
from app.db.repositories.jobs import JobRepository
from app.domains.jobs.types import JobStatus, JobType
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class JobRunner:
    """Executes asynchronous background jobs with retries and attempt logging."""

    def __init__(self, job_repository: JobRepository | None = None) -> None:
        self._job_repository = job_repository or JobRepository()

    async def execute_job(
        self, session: AsyncSession, job: Job
    ) -> tuple[JobStatus, dict[str, Any] | None, str | None]:
        """Run simulated job execution based on job type."""
        job.started_at = datetime.now(UTC)
        job.status = JobStatus.PROCESSING.value
        job.attempt_count += 1
        await session.flush()

        start_time = datetime.now(UTC)
        attempt_number = job.attempt_count

        try:
            logger.info(
                "Executing job %s (type=%s, attempt=%d)", job.id, job.job_type, attempt_number
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
            elif job.job_type == JobType.MODEL_EVALUATION.value:
                result = {
                    "accuracy": 0.942,
                    "f1_score": 0.938,
                    "latency_p95_ms": 14.2,
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
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error_str = str(exc) or "Job processing failed."

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
