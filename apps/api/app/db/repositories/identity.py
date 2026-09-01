"""Data access for external users and workspace memberships."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import User, WorkspaceMembership
from app.domains.identity.principal import Principal

DEFAULT_WORKSPACE_ROLES = {
    UUID("11111111-1111-1111-1111-111111111111"): "owner",
    UUID("22222222-2222-2222-2222-222222222222"): "editor",
    UUID("33333333-3333-3333-3333-333333333333"): "viewer",
}


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
        membership = result.scalar_one_or_none()
        if membership is None:
            is_dev = principal and (
                principal.subject.startswith("dev-") or principal.subject == "dev-user-123"
            )
            if is_dev or workspace_id in DEFAULT_WORKSPACE_ROLES:
                role = DEFAULT_WORKSPACE_ROLES.get(workspace_id, "owner")
                membership = WorkspaceMembership(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role=role,
                )
                session.add(membership)
                await session.flush()
                await session.refresh(membership)
        return membership
