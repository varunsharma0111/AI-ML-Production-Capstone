"""REST endpoints for model versioning, evaluation quality gates, and controlled inference."""

from __future__ import annotations

from uuid import UUID

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_session,
)
from app.api.schemas.ml import (
    ModelCreate,
    ModelEvaluateRequest,
    ModelResponse,
    PredictRequest,
    PredictResponse,
)
from app.domains.identity.principal import Principal
from app.services.ml import MLService
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/models", tags=["ml"])
_ml_service = MLService()


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    payload: ModelCreate,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    model = await _ml_service.register_and_train_model(session, principal, payload)
    return ModelResponse.model_validate(model)


@router.get("", response_model=list[ModelResponse])
async def list_models(
    session: AsyncSession = Depends(get_session),
) -> list[ModelResponse]:
    models = await _ml_service.list_models(session)
    return [ModelResponse.model_validate(m) for m in models]


@router.post("/{model_id}/evaluate", response_model=ModelResponse)
async def evaluate_model(
    model_id: UUID,
    payload: ModelEvaluateRequest,
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    model, _ = await _ml_service.evaluate_model(session, model_id, payload)
    return ModelResponse.model_validate(model)


@router.post("/{model_id}/predict", response_model=PredictResponse)
async def predict(
    model_id: UUID,
    payload: PredictRequest,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> PredictResponse:
    prediction, latency_ms = await _ml_service.predict(session, principal, model_id, payload)
    return PredictResponse(
        model_version_id=model_id,
        prediction=prediction,
        latency_ms=latency_ms,
    )
