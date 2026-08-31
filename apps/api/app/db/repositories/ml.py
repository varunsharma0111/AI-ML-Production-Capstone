"""Model registry and inference logging repository."""

from __future__ import annotations

from uuid import UUID

from app.db.models.entities import InferenceLog, ModelEvaluation, ModelVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ModelRepository:
    async def create_model_version(
        self, session: AsyncSession, model: ModelVersion
    ) -> ModelVersion:
        session.add(model)
        await session.flush()
        await session.refresh(model)
        return model

    async def get_model_version(self, session: AsyncSession, model_id: UUID) -> ModelVersion | None:
        result = await session.execute(select(ModelVersion).where(ModelVersion.id == model_id))
        return result.scalar_one_or_none()

    async def list_model_versions(self, session: AsyncSession) -> list[ModelVersion]:
        result = await session.execute(
            select(ModelVersion).order_by(ModelVersion.created_at.desc())
        )
        return list(result.scalars())

    async def list_model_versions_for_workspace(
        self, session: AsyncSession, workspace_id: UUID
    ) -> list[ModelVersion]:
        result = await session.execute(
            select(ModelVersion)
            .where(ModelVersion.workspace_id == workspace_id)
            .order_by(ModelVersion.created_at.desc())
        )
        return list(result.scalars())

    async def record_evaluation(
        self, session: AsyncSession, evaluation: ModelEvaluation
    ) -> ModelEvaluation:
        session.add(evaluation)
        await session.flush()
        await session.refresh(evaluation)
        return evaluation

    async def get_latest_evaluation(
        self, session: AsyncSession, model_version_id: UUID
    ) -> ModelEvaluation | None:
        result = await session.execute(
            select(ModelEvaluation)
            .where(ModelEvaluation.model_version_id == model_version_id)
            .order_by(ModelEvaluation.evaluated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def record_inference_log(self, session: AsyncSession, log: InferenceLog) -> InferenceLog:
        session.add(log)
        await session.flush()
        return log

    async def list_inference_logs_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, limit: int = 100
    ) -> list[InferenceLog]:
        result = await session.execute(
            select(InferenceLog)
            .where(InferenceLog.workspace_id == workspace_id)
            .order_by(InferenceLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())
