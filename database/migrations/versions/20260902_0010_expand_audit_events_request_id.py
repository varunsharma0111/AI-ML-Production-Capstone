"""Expand audit_events request_id column length to 100 characters.

Revision ID: 20260902_0010
Revises: 20260902_0009
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0010"
down_revision: str | Sequence[str] | None = "20260902_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "audit_events",
        "request_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=100),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_events",
        "request_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=36),
        existing_nullable=False,
    )
