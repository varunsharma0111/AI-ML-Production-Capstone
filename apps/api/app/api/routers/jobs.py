"""REST endpoints for workspace-scoped job submission, querying, and cancellation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_redis_manager,
    get_request_id,
    get_session,
)
from app.api.schemas.jobs import JobListResponse, JobResponse, JobSubmit, TrainingJobCreate
from app.core.redis import RedisManager
from app.domains.identity.principal import Principal
from app.services.jobs import JobService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/jobs", tags=["jobs"])
global_jobs_router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@global_jobs_router.post("/train", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_training_job(
    payload: TrainingJobCreate,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
    redis_manager: RedisManager | None = Depends(get_redis_manager),
) -> JobResponse:
    job_service = JobService(redis_manager=redis_manager)
    job = await job_service.submit_training_job(session, principal, payload, request_id)
    return JobResponse.model_validate(job)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(
    workspace_id: UUID,
    payload: JobSubmit,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
    redis_manager: RedisManager | None = Depends(get_redis_manager),
) -> JobResponse:
    job_service = JobService(redis_manager=redis_manager)
    job = await job_service.submit_job(session, principal, workspace_id, payload, request_id)
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    workspace_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> JobListResponse:
    job_service = JobService()
    jobs = await job_service.list_jobs(session, principal, workspace_id, offset, limit)
    return JobListResponse(
        items=[JobResponse.model_validate(job) for job in jobs],
        offset=offset,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    workspace_id: UUID,
    job_id: UUID,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    job_service = JobService()
    job = await job_service.get_job(session, principal, workspace_id, job_id)
    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    workspace_id: UUID,
    job_id: UUID,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> JobResponse:
    job_service = JobService()
    job = await job_service.cancel_job(session, principal, workspace_id, job_id, request_id)
    return JobResponse.model_validate(job)
