"""Data access for external users and workspace memberships."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import User, Workspace, WorkspaceMembership
from app.domains.identity.principal import Principal

PUBLIC_TEST_WORKSPACE_ID = UUID("00000000-0000-4000-a000-000000000001")


class IdentityRepository:
    async def get_or_create_user(self, session: AsyncSession, principal: Principal) -> User:
        from app.core.config import get_settings

        settings = get_settings()

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
                ws_id = PUBLIC_TEST_WORKSPACE_ID if settings.public_test_mode else uuid4()
                ws_slug = "public-test-workspace" if settings.public_test_mode else "default"
                ws_name = "Public Test Workspace" if settings.public_test_mode else "Default Workspace"
                new_ws = Workspace(id=ws_id, slug=ws_slug, name=ws_name)
                session.add(new_ws)
                await session.flush()
                await session.refresh(new_ws)
                workspaces = [new_ws]

            for ws in workspaces:
                session.add(WorkspaceMembership(workspace_id=ws.id, user_id=user.id, role="owner"))
            await session.flush()
        else:
            # Upgrade any existing non-owner memberships for this user to owner (Admin)
            mem_result = await session.execute(
                select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id)
            )
            memberships = mem_result.scalars().all()
            if not memberships:
                ws_result = await session.execute(select(Workspace))
                workspaces = ws_result.scalars().all()
                if not workspaces:
                    ws_id = PUBLIC_TEST_WORKSPACE_ID if settings.public_test_mode else uuid4()
                    ws_slug = "public-test-workspace" if settings.public_test_mode else "default"
                    ws_name = "Public Test Workspace" if settings.public_test_mode else "Default Workspace"
                    new_ws = Workspace(id=ws_id, slug=ws_slug, name=ws_name)
                    session.add(new_ws)
                    await session.flush()
                    await session.refresh(new_ws)
                    workspaces = [new_ws]

                for ws in workspaces:
                    session.add(
                        WorkspaceMembership(workspace_id=ws.id, user_id=user.id, role="owner")
                    )
                await session.flush()
            else:
                updated = False
                for m in memberships:
                    if m.role != "owner":
                        m.role = "owner"
                        updated = True
                if updated:
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
        membership = result.scalar_one_or_none()
        if membership is None:
            from app.core.config import get_settings

            settings = get_settings()
            if settings.public_test_mode or settings.dev_auth_mode or settings.app_env != "production":
                ws_res = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
                ws = ws_res.scalar_one_or_none()
                if ws is None:
                    if settings.public_test_mode and workspace_id != PUBLIC_TEST_WORKSPACE_ID:
                        # In public test mode, do not spawn arbitrary new workspaces for non-existent workspace IDs
                        return None
                    ws = Workspace(
                        id=workspace_id,
                        slug="public-test-workspace" if (settings.public_test_mode and workspace_id == PUBLIC_TEST_WORKSPACE_ID) else f"ws-{str(workspace_id)[:8]}",
                        name="Public Test Workspace" if settings.public_test_mode else "Development Workspace",
                    )
                    session.add(ws)
                    await session.flush()

                membership = WorkspaceMembership(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role="owner",
                )
                session.add(membership)
                await session.flush()

        return membership

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
