"""REST endpoints for Operations Dashboard telemetry and workspace Audit Logs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_session,
)
from app.api.schemas.operations import (
    AuditEventResponse,
    OperationsDashboardResponse,
)
from app.domains.identity.principal import Principal
from app.services.operations import OperationsService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}", tags=["operations"])
_operations_service = OperationsService()


@router.get("/operations/dashboard", response_model=OperationsDashboardResponse)
async def get_operations_dashboard(
    workspace_id: UUID,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> OperationsDashboardResponse:
    return await _operations_service.get_dashboard_telemetry(session, principal, workspace_id)


@router.get("/audit-logs", response_model=list[AuditEventResponse])
async def list_audit_logs(
    workspace_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> list[AuditEventResponse]:
    return await _operations_service.list_audit_logs(session, principal, workspace_id, limit=limit)
