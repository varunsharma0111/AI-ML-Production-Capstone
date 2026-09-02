"""Seed public test user and workspace.

Revision ID: 20260902_0009
Revises: 20260830_0008
Create Date: 2026-09-02
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0009"
down_revision: str | Sequence[str] | None = "20260830_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PUBLIC_USER_ID = UUID("00000000-0000-4000-a000-000000000002")
PUBLIC_WORKSPACE_ID = UUID("00000000-0000-4000-a000-000000000001")


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
                "id": PUBLIC_USER_ID,
                "oidc_subject": "public-test-user-id",
                "email": "public.test@auraml.local",
                "display_name": "Public Test User",
            }
        ],
    )

    op.bulk_insert(
        workspaces_table,
        [
            {
                "id": PUBLIC_WORKSPACE_ID,
                "slug": "public-test-workspace",
                "name": "Public Test Workspace",
            },
        ],
    )

    op.bulk_insert(
        memberships_table,
        [
            {
                "id": UUID("00000000-0000-4000-a000-000000000003"),
                "workspace_id": PUBLIC_WORKSPACE_ID,
                "user_id": PUBLIC_USER_ID,
                "role": "owner",
            },
        ],
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM workspace_memberships WHERE user_id = '{PUBLIC_USER_ID}'")
    op.execute(f"DELETE FROM workspaces WHERE id = '{PUBLIC_WORKSPACE_ID}'")
    op.execute(f"DELETE FROM users WHERE id = '{PUBLIC_USER_ID}'")
