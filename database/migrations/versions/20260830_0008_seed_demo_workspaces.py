"""Seed demo workspaces and dev user membership.

Revision ID: 20260830_0008
Revises: 20260830_0007
Create Date: 2026-08-30
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0008"
down_revision: str | Sequence[str] | None = "20260830_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
WS1_ID = UUID("11111111-1111-1111-1111-111111111111")
WS2_ID = UUID("22222222-2222-2222-2222-222222222222")
WS3_ID = UUID("33333333-3333-3333-3333-333333333333")


def upgrade() -> None:
    users_table = sa.table(
        "users",
        sa.column("id", sa.Uuid),
        sa.column("oidc_subject", sa.String),
        sa.column("email", sa.String),
        sa.column("display_name", sa.String),
    )
    workspaces_table = sa.table(
        "workspaces",
        sa.column("id", sa.Uuid),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
    )
    memberships_table = sa.table(
        "workspace_memberships",
        sa.column("id", sa.Uuid),
        sa.column("workspace_id", sa.Uuid),
        sa.column("user_id", sa.Uuid),
        sa.column("role", sa.String),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "id": DEV_USER_ID,
                "oidc_subject": "dev-user-123",
                "email": "dev.user@example.com",
                "display_name": "Dev Demo User",
            }
        ],
    )

    op.bulk_insert(
        workspaces_table,
        [
            {"id": WS1_ID, "slug": "demo-workspace-1", "name": "Demo Production Workspace"},
            {"id": WS2_ID, "slug": "demo-workspace-2", "name": "Staging Analytics Workspace"},
            {"id": WS3_ID, "slug": "demo-workspace-3", "name": "Research Workspace"},
        ],
    )

    op.bulk_insert(
        memberships_table,
        [
            {
                "id": UUID("a1111111-1111-1111-1111-111111111111"),
                "workspace_id": WS1_ID,
                "user_id": DEV_USER_ID,
                "role": "owner",
            },
            {
                "id": UUID("a2222222-2222-2222-2222-222222222222"),
                "workspace_id": WS2_ID,
                "user_id": DEV_USER_ID,
                "role": "editor",
            },
            {
                "id": UUID("a3333333-3333-3333-3333-333333333333"),
                "workspace_id": WS3_ID,
                "user_id": DEV_USER_ID,
                "role": "viewer",
            },
        ],
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM workspace_memberships WHERE user_id = '{DEV_USER_ID}'")
    op.execute(f"DELETE FROM workspaces WHERE id IN ('{WS1_ID}', '{WS2_ID}', '{WS3_ID}')")
    op.execute(f"DELETE FROM users WHERE id = '{DEV_USER_ID}'")
