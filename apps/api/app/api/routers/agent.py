"""REST endpoints for listing and executing sandboxed AI agent tools."""

from __future__ import annotations

from app.api.dependencies.request import (
    get_authenticated_principal,
    get_request_id,
    get_session,
)
from app.api.schemas.agent import (
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolSummaryResponse,
)
from app.domains.identity.principal import Principal
from app.services.agent import AgentService
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agent/tools", tags=["agent"])
_agent_service = AgentService()


@router.get("", response_model=list[ToolSummaryResponse])
async def list_agent_tools() -> list[ToolSummaryResponse]:
    tools = _agent_service.list_tools()
    return [ToolSummaryResponse.model_validate(t) for t in tools]


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_agent_tool(
    payload: ToolExecuteRequest,
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
) -> ToolExecuteResponse:
    result, duration_ms = await _agent_service.execute_tool(session, principal, payload, request_id)
    return ToolExecuteResponse(
        tool_name=payload.tool_name,
        result=result,
        duration_ms=duration_ms,
    )
