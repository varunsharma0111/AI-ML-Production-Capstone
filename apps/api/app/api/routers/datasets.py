"""REST endpoints for dataset upload, listing, and automated profiling statistics."""

from __future__ import annotations

from uuid import UUID

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_redis_manager,
    get_request_id,
    get_session,
)
from app.api.schemas.datasets import (
    DatasetListResponse,
    DatasetProfileResponse,
    DatasetResponse,
    DatasetUploadResponse,
)
from app.core.redis import RedisManager
from app.domains.identity.principal import Principal
from app.services.datasets import DatasetService
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    workspace_id: UUID = Form(...),
    file: UploadFile = File(...),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
    redis_manager: RedisManager | None = Depends(get_redis_manager),
) -> DatasetUploadResponse:
    file_content = await file.read()
    dataset_service = DatasetService(redis_manager=redis_manager)
    dataset, job = await dataset_service.upload_dataset(
        session=session,
        principal=principal,
        workspace_id=workspace_id,
        filename=file.filename or "dataset.csv",
        file_content=file_content,
        content_type=file.content_type,
        request_id=request_id,
    )
    return DatasetUploadResponse(
        dataset=DatasetResponse.model_validate(dataset),
        job_id=job.id if job else None,
    )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    workspace_id: UUID = Query(...),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> DatasetListResponse:
    dataset_service = DatasetService()
    datasets = await dataset_service.list_datasets(
        session=session,
        principal=principal,
        workspace_id=workspace_id,
        offset=offset,
        limit=limit,
    )
    return DatasetListResponse(
        items=[DatasetResponse.model_validate(d) for d in datasets],
        offset=offset,
        limit=limit,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: UUID,
    workspace_id: UUID = Query(...),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> DatasetResponse:
    dataset_service = DatasetService()
    dataset = await dataset_service.get_dataset(
        session=session,
        principal=principal,
        workspace_id=workspace_id,
        dataset_id=dataset_id,
    )
    return DatasetResponse.model_validate(dataset)


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
async def get_dataset_profile(
    dataset_id: UUID,
    workspace_id: UUID = Query(...),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> DatasetProfileResponse:
    dataset_service = DatasetService()
    profile = await dataset_service.get_profile(
        session=session,
        principal=principal,
        workspace_id=workspace_id,
        dataset_id=dataset_id,
    )
    return DatasetProfileResponse.model_validate(profile)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: UUID,
    workspace_id: UUID = Query(...),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> None:
    dataset_service = DatasetService()
    await dataset_service.delete_dataset(
        session=session,
        principal=principal,
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        request_id=request_id,
    )
