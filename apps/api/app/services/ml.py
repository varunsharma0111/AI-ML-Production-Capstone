"""ML lifecycle, quality gate evaluation, promotion, and controlled inference service."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.api.schemas.ml import (
    ModelCreate,
    ModelEvaluateRequest,
    ModelPromoteRequest,
    PredictRequest,
    QualityGateResponse,
)
from app.core.errors import AuthorizationError, ConflictError, ResourceNotFoundError, ValidationError
from app.db.models.entities import AuditEvent, InferenceLog, ModelEvaluation, ModelVersion
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.ml import ModelRepository
from app.domains.identity.policy import Permission, WorkspaceRole, require_permission
from app.domains.identity.principal import Principal
from app.domains.ml.types import DEFAULT_ACCURACY_THRESHOLD, DEFAULT_F1_SCORE_THRESHOLD, ModelStatus
from sqlalchemy.ext.asyncio import AsyncSession

from ml.evaluation.evaluator import ModelEvaluator
from ml.training.trainer import ModelTrainer
from services.ml_inference.predictor import ControlledInferencePredictor


class MLService:
    def __init__(
        self,
        identity_repository: IdentityRepository | None = None,
        model_repository: ModelRepository | None = None,
        trainer: ModelTrainer | None = None,
        evaluator: ModelEvaluator | None = None,
        predictor: ControlledInferencePredictor | None = None,
    ) -> None:
        self._identity_repository = identity_repository or IdentityRepository()
        self._model_repository = model_repository or ModelRepository()
        self._trainer = trainer or ModelTrainer()
        self._evaluator = evaluator or ModelEvaluator()
        self._predictor = predictor or ControlledInferencePredictor()

    async def _authorized_user(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        required_permission: Permission,
    ):
        user = await self._identity_repository.get_or_create_user(session, principal)
        membership = await self._identity_repository.get_membership(
            session, workspace_id, user.id
        )
        if membership is None:
            raise AuthorizationError("You are not a member of this workspace.")
        require_permission(membership.role, required_permission)
        return user, membership

    async def register_and_train_model(
        self, session: AsyncSession, principal: Principal, payload: ModelCreate
    ) -> ModelVersion:
        async with session.begin():
            user, _ = await self._authorized_user(
                session, principal, payload.workspace_id, Permission.MODEL_EVALUATE
            )
            artifact_path = self._trainer.train_model(
                payload.name, payload.version_tag, payload.hyperparameters
            )

            model = ModelVersion(
                workspace_id=payload.workspace_id,
                name=payload.name,
                version_tag=payload.version_tag,
                description=payload.description,
                artifact_path=artifact_path,
                status=ModelStatus.CANDIDATE.value,
                hyperparameters_json=payload.hyperparameters,
            )

            return await self._model_repository.create_model_version(session, model)

    async def list_models(
        self, session: AsyncSession, principal: Principal, workspace_id: UUID | None = None
    ) -> list[ModelVersion]:
        async with session.begin():
            if workspace_id:
                await self._authorized_user(
                    session, principal, workspace_id, Permission.MODEL_READ
                )
                return await self._model_repository.list_model_versions_for_workspace(
                    session, workspace_id
                )
            return await self._model_repository.list_model_versions(session)

    async def get_model(
        self, session: AsyncSession, principal: Principal, model_id: UUID, workspace_id: UUID | None = None
    ) -> ModelVersion:
        async with session.begin():
            model = await self._model_repository.get_model_version(session, model_id)
            if model is None:
                raise ResourceNotFoundError("Model version not found.")
            target_ws = workspace_id or model.workspace_id
            if target_ws:
                await self._authorized_user(session, principal, target_ws, Permission.MODEL_READ)
            return model

    async def evaluate_model(
        self,
        session: AsyncSession,
        principal: Principal,
        model_id: UUID,
        payload: ModelEvaluateRequest,
        request_id: str = "unknown",
    ) -> tuple[ModelVersion, ModelEvaluation]:
        async with session.begin():
            user, _ = await self._authorized_user(
                session, principal, payload.workspace_id, Permission.MODEL_EVALUATE
            )

            model = await self._model_repository.get_model_version(session, model_id)
            if model is None:
                raise ResourceNotFoundError("Model version not found.")

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="model.evaluation_started",
                    resource_type="model_version",
                    resource_id=model.id,
                    request_id=request_id,
                    metadata_json={"model_name": model.name, "version_tag": model.version_tag},
                )
            )

            # Accuracy & F1 metric extraction logic (from payload or stored metrics_json)
            metrics = model.metrics_json or {}
            accuracy = (
                payload.accuracy
                if payload.accuracy is not None
                else float(metrics.get("accuracy", 0.0))
            )
            f1_score = (
                payload.f1_score
                if payload.f1_score is not None
                else float(metrics.get("f1_score", 0.0))
            )

            acc_thresh = payload.accuracy_threshold or DEFAULT_ACCURACY_THRESHOLD
            f1_thresh = payload.f1_threshold or DEFAULT_F1_SCORE_THRESHOLD

            passed_gate, metadata = self._evaluator.evaluate(
                accuracy=accuracy,
                f1_score=f1_score,
                latency_ms=payload.latency_ms,
                accuracy_threshold=acc_thresh,
                f1_threshold=f1_thresh,
            )

            metadata["evaluator_user_id"] = str(user.id)
            metadata["workspace_id"] = str(payload.workspace_id)
            metadata["model_name"] = model.name
            metadata["version_tag"] = model.version_tag

            evaluation = ModelEvaluation(
                model_version_id=model.id,
                accuracy=accuracy,
                f1_score=f1_score,
                latency_ms=payload.latency_ms,
                passed_gate=passed_gate,
                evaluation_metadata=metadata,
            )
            await self._model_repository.record_evaluation(session, evaluation)

            if passed_gate:
                model.status = ModelStatus.APPROVED.value
                decision_action = "model.approved"
            else:
                model.status = ModelStatus.REJECTED.value
                decision_action = "model.rejected"

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action=decision_action,
                    resource_type="model_version",
                    resource_id=model.id,
                    request_id=request_id,
                    metadata_json=metadata,
                )
            )

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="model.evaluation_completed",
                    resource_type="model_version",
                    resource_id=model.id,
                    request_id=request_id,
                    metadata_json={"passed_gate": passed_gate, "status": model.status},
                )
            )

            await session.flush()
            return model, evaluation

    async def promote_model(
        self,
        session: AsyncSession,
        principal: Principal,
        model_id: UUID,
        payload: ModelPromoteRequest,
        request_id: str = "unknown",
    ) -> ModelVersion:
        async with session.begin():
            user, membership = await self._authorized_user(
                session, principal, payload.workspace_id, Permission.MODEL_PROMOTE
            )

            model = await self._model_repository.get_model_version(session, model_id)
            if model is None:
                raise ResourceNotFoundError("Model version not found.")

            target_status = payload.target_status.lower()

            # State Transition Safeguards
            if model.status == ModelStatus.REJECTED.value:
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="model.promotion_denied",
                        resource_type="model_version",
                        resource_id=model.id,
                        request_id=request_id,
                        metadata_json={"reason": "Cannot promote a REJECTED model version", "current_status": model.status},
                    )
                )
                raise ValidationError("Cannot promote a REJECTED model version.")

            if model.status in [ModelStatus.CANDIDATE.value, ModelStatus.DRAFT.value]:
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="model.promotion_denied",
                        resource_type="model_version",
                        resource_id=model.id,
                        request_id=request_id,
                        metadata_json={"reason": "Model must be evaluated and APPROVED before promotion", "current_status": model.status},
                    )
                )
                raise ValidationError("Model must pass quality gate evaluation (APPROVED status) before promotion.")

            if target_status == ModelStatus.PRODUCTION.value and membership.role != WorkspaceRole.OWNER.value:
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="model.promotion_denied",
                        resource_type="model_version",
                        resource_id=model.id,
                        request_id=request_id,
                        metadata_json={"reason": "Only workspace owners can promote models to production"},
                    )
                )
                raise AuthorizationError("Only workspace owners can promote models to production.")

            if target_status == ModelStatus.STAGING.value:
                if model.status not in [ModelStatus.APPROVED.value]:
                    session.add(
                        AuditEvent(
                            actor_user_id=user.id,
                            workspace_id=payload.workspace_id,
                            action="model.promotion_denied",
                            resource_type="model_version",
                            resource_id=model.id,
                            request_id=request_id,
                            metadata_json={"reason": f"Invalid transition from {model.status} to staging"},
                        )
                    )
                    raise ValidationError(f"Cannot transition model from '{model.status}' to STAGING.")
                model.status = ModelStatus.STAGING.value
                audit_action = "model.promoted_staging"

            elif target_status == ModelStatus.PRODUCTION.value:
                if model.status not in [ModelStatus.APPROVED.value, ModelStatus.STAGING.value]:
                    session.add(
                        AuditEvent(
                            actor_user_id=user.id,
                            workspace_id=payload.workspace_id,
                            action="model.promotion_denied",
                            resource_type="model_version",
                            resource_id=model.id,
                            request_id=request_id,
                            metadata_json={"reason": f"Invalid transition from {model.status} to production"},
                        )
                    )
                    raise ValidationError(f"Cannot transition model from '{model.status}' to PRODUCTION.")
                model.status = ModelStatus.PRODUCTION.value
                audit_action = "model.promoted_production"
            else:
                raise ValidationError(f"Invalid promotion target status '{target_status}'.")

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action=audit_action,
                    resource_type="model_version",
                    resource_id=model.id,
                    request_id=request_id,
                    metadata_json={"previous_status": model.status, "new_status": target_status},
                )
            )

            await session.flush()
            return model

    async def get_quality_gate(
        self, session: AsyncSession, principal: Principal, model_id: UUID, workspace_id: UUID
    ) -> QualityGateResponse:
        async with session.begin():
            await self._authorized_user(session, principal, workspace_id, Permission.MODEL_READ)
            model = await self._model_repository.get_model_version(session, model_id)
            if model is None:
                raise ResourceNotFoundError("Model version not found.")

            evaluation = await self._model_repository.get_latest_evaluation(session, model.id)
            if evaluation is None:
                # Construct synthetic candidate quality gate status from metrics_json if not yet evaluated
                metrics = model.metrics_json or {}
                acc = float(metrics.get("accuracy", 0.0))
                f1 = float(metrics.get("f1_score", 0.0))
                passed, meta = self._evaluator.evaluate(acc, f1)
                return QualityGateResponse(
                    model_id=model.id,
                    workspace_id=workspace_id,
                    status=model.status,
                    passed_gate=passed,
                    accuracy=acc,
                    f1_score=f1,
                    accuracy_threshold=meta["accuracy_threshold"],
                    f1_threshold=meta["f1_threshold"],
                    failure_reasons=meta["failure_reasons"],
                    evaluated_at=model.created_at,
                )

            meta = evaluation.evaluation_metadata or {}
            return QualityGateResponse(
                model_id=model.id,
                workspace_id=workspace_id,
                status=model.status,
                passed_gate=evaluation.passed_gate,
                accuracy=evaluation.accuracy,
                f1_score=evaluation.f1_score,
                accuracy_threshold=float(meta.get("accuracy_threshold", DEFAULT_ACCURACY_THRESHOLD)),
                f1_threshold=float(meta.get("f1_threshold", DEFAULT_F1_SCORE_THRESHOLD)),
                failure_reasons=list(meta.get("failure_reasons", [])),
                evaluated_at=evaluation.evaluated_at,
            )

    async def predict(
        self,
        session: AsyncSession,
        principal: Principal,
        model_id: UUID,
        payload: PredictRequest,
        request_id: str = "unknown",
    ) -> tuple[dict[str, object], float, str]:
        async with session.begin():
            user, _ = await self._authorized_user(
                session, principal, payload.workspace_id, Permission.MODEL_READ
            )

            model = await self._model_repository.get_model_version(session, model_id)
            if model is None or (model.workspace_id is not None and model.workspace_id != payload.workspace_id):
                raise ResourceNotFoundError("Model version not found.")

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="model.inference_requested",
                    resource_type="model_version",
                    resource_id=model.id,
                    request_id=request_id,
                    metadata_json={"model_name": model.name, "version_tag": model.version_tag},
                )
            )

            try:
                prediction_result, latency_ms = self._predictor.predict(
                    model.status, model.artifact_path, payload.input_features
                )
            except Exception as error:
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="model.inference_failed",
                        resource_type="model_version",
                        resource_id=model.id,
                        request_id=request_id,
                        metadata_json={"error": str(error), "model_status": model.status},
                    )
                )
                raise error

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="model.inference_completed",
                    resource_type="model_version",
                    resource_id=model.id,
                    request_id=request_id,
                    metadata_json={
                        "prediction": prediction_result.get("prediction"),
                        "confidence": prediction_result.get("confidence"),
                        "latency_ms": latency_ms,
                    },
                )
            )

            inference_log = InferenceLog(
                model_version_id=model.id,
                workspace_id=payload.workspace_id,
                input_features=payload.input_features,
                prediction=prediction_result,
                latency_ms=latency_ms,
            )
            await self._model_repository.record_inference_log(session, inference_log)

            await session.flush()
            return prediction_result, latency_ms, model.version_tag

    async def list_inference_logs(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        limit: int = 100,
    ) -> list[InferenceLog]:
        async with session.begin():
            await self._authorized_user(session, principal, workspace_id, Permission.MODEL_READ)
            return await self._model_repository.list_inference_logs_for_workspace(
                session, workspace_id, limit=limit
            )

