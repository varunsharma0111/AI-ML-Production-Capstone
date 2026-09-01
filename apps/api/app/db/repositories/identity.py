"""Data access for external users and workspace memberships."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import User, Workspace, WorkspaceMembership
from app.domains.identity.principal import Principal


class IdentityRepository:
    async def get_or_create_user(self, session: AsyncSession, principal: Principal) -> User:
        result = await session.execute(select(User).where(User.oidc_subject == principal.subject))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                oidc_subject=principal.subject,
                email=principal.email,
                display_name=principal.display_name,
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)

            # Auto-assign initial user memberships to available workspaces if any exist
            ws_result = await session.execute(select(Workspace))
            workspaces = ws_result.scalars().all()
            if not workspaces:
                # Create a default workspace for the user if database has none
                new_ws = Workspace(slug="default", name="Default Workspace")
                session.add(new_ws)
                await session.flush()
                await session.refresh(new_ws)
                workspaces = [new_ws]

            for ws in workspaces:
                session.add(WorkspaceMembership(workspace_id=ws.id, user_id=user.id, role="owner"))
            await session.flush()

        return user

    async def get_membership(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        principal: Principal | None = None,
    ) -> WorkspaceMembership | None:
        result = await session.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_workspaces(
        self, session: AsyncSession, user_id: UUID
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Workspace.id, Workspace.slug, Workspace.name, WorkspaceMembership.role)
            .join(WorkspaceMembership, Workspace.id == WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_id == user_id)
        )
        result = await session.execute(stmt)
        return [
            {
                "id": row[0],
                "slug": row[1],
                "name": row[2],
                "role": row[3],
            }
            for row in result.all()
        ]
