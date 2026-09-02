"""Milestone 3 Quality Gate schema updates for ModelEvaluations.

Revision ID: 20260830_0007
Revises: 20260830_0006
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0007"
down_revision: str | Sequence[str] | None = "20260830_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = [c["name"] for c in inspector.get_columns("model_evaluations")]
    if "workspace_id" not in existing_cols:
        op.add_column(
            "model_evaluations",
            sa.Column(
                "workspace_id",
                sa.UUID(),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("model_evaluations")]
    if "idx_model_evaluations_workspace_id" not in existing_indexes:
        op.create_index(
            "idx_model_evaluations_workspace_id",
            "model_evaluations",
            ["workspace_id"],
        )


def downgrade() -> None:
    op.drop_index("idx_model_evaluations_workspace_id", table_name="model_evaluations")
    op.drop_column("model_evaluations", "workspace_id")
