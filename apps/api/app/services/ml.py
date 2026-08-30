"""ML lifecycle and controlled inference service."""

from __future__ import annotations

from uuid import UUID

from app.api.schemas.ml import ModelCreate, ModelEvaluateRequest, PredictRequest
from app.core.errors import ResourceNotFoundError
from app.db.models.entities import InferenceLog, ModelEvaluation, ModelVersion
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.ml import ModelRepository
from app.domains.identity.policy import Permission, require_permission
from app.domains.identity.principal import Principal
from app.domains.ml.types import ModelStatus
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

    async def register_and_train_model(
        self, session: AsyncSession, principal: Principal, payload: ModelCreate
    ) -> ModelVersion:
        async with session.begin():
            artifact_path = self._trainer.train_model(
                payload.name, payload.version_tag, payload.hyperparameters
            )

            model = ModelVersion(
                name=payload.name,
                version_tag=payload.version_tag,
                description=payload.description,
                artifact_path=artifact_path,
                status=ModelStatus.DRAFT.value,
            )

            return await self._model_repository.create_model_version(session, model)

    async def list_models(self, session: AsyncSession) -> list[ModelVersion]:
        async with session.begin():
            return await self._model_repository.list_model_versions(session)

    async def evaluate_model(
        self, session: AsyncSession, model_id: UUID, payload: ModelEvaluateRequest
    ) -> tuple[ModelVersion, ModelEvaluation]:
        async with session.begin():
            model = await self._model_repository.get_model_version(session, model_id)
            if model is None:
                raise ResourceNotFoundError("Model version not found.")

            passed_gate, metadata = self._evaluator.evaluate(
                payload.accuracy, payload.f1_score, payload.latency_ms
            )

            evaluation = ModelEvaluation(
                model_version_id=model.id,
                accuracy=payload.accuracy,
                f1_score=payload.f1_score,
                latency_ms=payload.latency_ms,
                passed_gate=passed_gate,
                evaluation_metadata=metadata,
            )
            await self._model_repository.record_evaluation(session, evaluation)

            if passed_gate:
                model.status = ModelStatus.APPROVED.value
            else:
                model.status = ModelStatus.EVALUATED.value

            await session.flush()
            return model, evaluation

    async def predict(
        self, session: AsyncSession, principal: Principal, model_id: UUID, payload: PredictRequest
    ) -> tuple[dict[str, object], float]:
        async with session.begin():
            user = await self._identity_repository.get_or_create_user(session, principal)
            membership = await self._identity_repository.get_membership(
                session, payload.workspace_id, user.id
            )
            if membership is None:
                from app.core.errors import AuthorizationError

                raise AuthorizationError("You are not a member of this workspace.")
            require_permission(membership.role, Permission.TASK_READ)

            model = await self._model_repository.get_model_version(session, model_id)
            if model is None:
                raise ResourceNotFoundError("Model version not found.")

            # Predict (raises DomainError if status != 'approved')
            prediction_result, latency_ms = self._predictor.predict(
                model.status, model.artifact_path, payload.input_features
            )

            inference_log = InferenceLog(
                model_version_id=model.id,
                workspace_id=payload.workspace_id,
                input_features=payload.input_features,
                prediction=prediction_result,
                latency_ms=latency_ms,
            )
            await self._model_repository.record_inference_log(session, inference_log)

            return prediction_result, latency_ms
