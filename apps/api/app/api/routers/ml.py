"""REST endpoints for model versioning, quality gate evaluation, model promotion, controlled inference, and prediction history."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_request_id,
    get_session,
)
from app.api.schemas.ml import (
    ModelCreate,
    ModelEvaluateRequest,
    ModelPromoteRequest,
    ModelResponse,
    PredictionLogResponse,
    PredictRequest,
    PredictResponse,
    QualityGateResponse,
)
from app.domains.identity.principal import Principal
from app.services.ml import MLService

router = APIRouter(prefix="/api/v1", tags=["ml"])
_ml_service = MLService()


@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    payload: ModelCreate,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    model = await _ml_service.register_and_train_model(session, principal, payload)
    return ModelResponse.model_validate(model)


@router.get("/models", response_model=list[ModelResponse])
async def list_models(
    workspace_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> list[ModelResponse]:
    models = await _ml_service.list_models(session, principal, workspace_id)
    return [ModelResponse.model_validate(m) for m in models]


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    workspace_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    model = await _ml_service.get_model(session, principal, model_id, workspace_id)
    return ModelResponse.model_validate(model)


@router.post("/models/{model_id}/evaluate", response_model=ModelResponse)
async def evaluate_model(
    model_id: UUID,
    payload: ModelEvaluateRequest,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> ModelResponse:
    model, _ = await _ml_service.evaluate_model(session, principal, model_id, payload, request_id)
    return ModelResponse.model_validate(model)


@router.post("/models/{model_id}/promote", response_model=ModelResponse)
async def promote_model(
    model_id: UUID,
    payload: ModelPromoteRequest,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> ModelResponse:
    model = await _ml_service.promote_model(session, principal, model_id, payload, request_id)
    return ModelResponse.model_validate(model)


@router.get("/models/{model_id}/quality-gate", response_model=QualityGateResponse)
async def get_quality_gate(
    model_id: UUID,
    workspace_id: UUID = Query(...),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> QualityGateResponse:
    return await _ml_service.get_quality_gate(session, principal, model_id, workspace_id)


@router.post("/models/{model_id}/predict", response_model=PredictResponse)
async def predict(
    model_id: UUID,
    payload: PredictRequest,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> PredictResponse:
    res, latency_ms, version_tag = await _ml_service.predict(
        session, principal, model_id, payload, request_id
    )
    return PredictResponse(
        model_id=model_id,
        model_version=version_tag,
        prediction=str(res.get("prediction", "unknown")),
        confidence=float(res.get("confidence", 0.0)),
        latency_ms=latency_ms,
    )


@router.get("/workspaces/{workspace_id}/predictions", response_model=list[PredictionLogResponse])
async def list_workspace_predictions(
    workspace_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> list[PredictionLogResponse]:
    logs = await _ml_service.list_inference_logs(session, principal, workspace_id, limit=limit)
    return [PredictionLogResponse.model_validate(log) for log in logs]
