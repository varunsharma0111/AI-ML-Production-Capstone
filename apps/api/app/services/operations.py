"""Business service for operational dashboard metrics and workspace audit logs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.operations import (
    AuditEventResponse,
    OperationsDashboardResponse,
    SystemMetricsSummary,
)
from app.db.models.entities import (
    AuditEvent,
    Dataset,
    InferenceLog,
    Job,
    ModelVersion,
    User,
    WorkspaceMembership,
)
from app.domains.identity.policy import Permission, PolicyEngine
from app.domains.identity.principal import Principal
from app.domains.identity.types import WorkspaceRole
from app.domains.shared.errors import AuthorizationError


class OperationsService:
    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self._policy_engine = policy_engine or PolicyEngine()

    async def _authorized_user(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        required_permission: Permission = Permission.WORKSPACE_READ,
    ) -> tuple[User, WorkspaceMembership]:
        user_result = await session.execute(
            select(User).where(User.oidc_subject == principal.subject)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise AuthorizationError("User profile not found.")

        membership_result = await session.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        membership = membership_result.scalar_one_or_none()
        if membership is None:
            raise AuthorizationError("Access denied: Not a member of workspace.")

        role = WorkspaceRole(membership.role)
        if not self._policy_engine.has_permission(role, required_permission):
            raise AuthorizationError(
                "Insufficient permissions for operational workspace telemetry."
            )

        return user, membership

    async def get_dashboard_telemetry(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
    ) -> OperationsDashboardResponse:
        async with session.begin():
            await self._authorized_user(session, principal, workspace_id, Permission.WORKSPACE_READ)

            # Datasets count
            ds_result = await session.execute(
                select(Dataset.status, func.count(Dataset.id))
                .where(Dataset.workspace_id == workspace_id)
                .group_by(Dataset.status)
            )
            ds_counts = dict(ds_result.all())

            # Jobs count
            job_result = await session.execute(
                select(Job.status, func.count(Job.id))
                .where(Job.workspace_id == workspace_id)
                .group_by(Job.status)
            )
            job_counts = dict(job_result.all())

            # Model count
            model_result = await session.execute(
                select(ModelVersion.status, func.count(ModelVersion.id))
                .where(ModelVersion.workspace_id == workspace_id)
                .group_by(ModelVersion.status)
            )
            model_counts = dict(model_result.all())

            # Inference count & avg latency
            inf_result = await session.execute(
                select(
                    func.count(InferenceLog.id),
                    func.coalesce(func.avg(InferenceLog.latency_ms), 0.0),
                ).where(InferenceLog.workspace_id == workspace_id)
            )
            total_predictions, avg_latency = inf_result.one()

            summary = SystemMetricsSummary(
                total_datasets=sum(ds_counts.values()),
                ready_datasets=ds_counts.get("ready", 0),
                profiling_datasets=ds_counts.get("profiling", 0),
                failed_datasets=ds_counts.get("failed", 0),
                total_training_jobs=sum(job_counts.values()),
                queued_jobs=job_counts.get("queued", 0),
                processing_jobs=job_counts.get("processing", 0),
                completed_jobs=job_counts.get("completed", 0),
                failed_jobs=job_counts.get("failed", 0),
                total_models=sum(model_counts.values()),
                production_models=model_counts.get("production", 0),
                staging_models=model_counts.get("staging", 0),
                approved_models=model_counts.get("approved", 0),
                rejected_models=model_counts.get("rejected", 0),
                total_predictions=total_predictions,
                average_latency_ms=round(float(avg_latency), 2),
            )

            return OperationsDashboardResponse(
                system_status="healthy",
                api_status="ok",
                database_status="ok",
                metrics=summary,
            )

    async def list_audit_logs(
        self,
        session: AsyncSession,
        principal: Principal,
        workspace_id: UUID,
        limit: int = 100,
    ) -> list[AuditEventResponse]:
        async with session.begin():
            await self._authorized_user(session, principal, workspace_id, Permission.WORKSPACE_READ)

            result = await session.execute(
                select(AuditEvent)
                .where(AuditEvent.workspace_id == workspace_id)
                .order_by(AuditEvent.occurred_at.desc())
                .limit(limit)
            )
            events = result.scalars().all()
            return [AuditEventResponse.model_validate(evt) for evt in events]
