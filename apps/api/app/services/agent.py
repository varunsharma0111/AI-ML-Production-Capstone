"""Transactional AI agent service with RBAC enforcement and audit logging."""

from __future__ import annotations

from uuid import UUID

from agent.tools.definitions import REGISTERED_TOOLS
from agent.tools.sandbox import ToolSandbox
from app.api.schemas.agent import ToolExecuteRequest
from app.db.models.entities import AuditEvent
from app.db.repositories.identity import IdentityRepository
from app.domains.identity.policy import Permission, require_permission
from app.domains.identity.principal import Principal
from sqlalchemy.ext.asyncio import AsyncSession


class AgentService:
    def __init__(
        self,
        identity_repository: IdentityRepository | None = None,
        sandbox: ToolSandbox | None = None,
    ) -> None:
        self._identity_repository = identity_repository or IdentityRepository()
        self._sandbox = sandbox or ToolSandbox()

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "required_permission": tool.required_permission,
            }
            for tool in REGISTERED_TOOLS.values()
        ]

    async def execute_tool(
        self,
        session: AsyncSession,
        principal: Principal,
        payload: ToolExecuteRequest,
        request_id: str,
    ) -> tuple[dict[str, object], float]:
        async with session.begin():
            user = await self._identity_repository.get_or_create_user(session, principal)
            membership = await self._identity_repository.get_membership(
                session, payload.workspace_id, user.id
            )
            if membership is None:
                from app.core.errors import AuthorizationError

                raise AuthorizationError("You are not a member of this workspace.")

            # Require task:read permission for workspace tools
            require_permission(membership.role, Permission.TASK_READ)

            result, duration_ms = self._sandbox.execute_tool(payload.tool_name, payload.arguments)

            audit_event = AuditEvent(
                actor_user_id=user.id,
                workspace_id=payload.workspace_id,
                action="agent.tool_executed",
                resource_type="agent_tool",
                resource_id=user.id,  # Associate with acting user
                request_id=request_id,
                metadata_json={
                    "tool_name": payload.tool_name,
                    "duration_ms": duration_ms,
                },
            )
            session.add(audit_event)

            return result, duration_ms
