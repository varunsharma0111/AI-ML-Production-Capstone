"""Data access for external users and workspace memberships."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import User, WorkspaceMembership
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
