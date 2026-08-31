"""Extend model_versions for Milestone 2.

Revision ID: 20260830_0006
Revises: 20260830_0005
Create Date: 2026-08-30 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0006"
down_revision: str | Sequence[str] | None = "20260830_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("model_versions", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.add_column("model_versions", sa.Column("dataset_id", sa.Uuid(), nullable=True))
    op.add_column("model_versions", sa.Column("job_id", sa.Uuid(), nullable=True))
    op.add_column(
        "model_versions",
        sa.Column(
            "metrics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "model_versions",
        sa.Column(
            "hyperparameters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )

    op.create_foreign_key(
        "fk_model_versions_workspace_id",
        "model_versions",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_model_versions_dataset_id",
        "model_versions",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_model_versions_job_id",
        "model_versions",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        op.f("ix_model_versions_workspace_id"),
        "model_versions",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_versions_dataset_id"),
        "model_versions",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_versions_job_id"),
        "model_versions",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_model_versions_job_id"), table_name="model_versions")
    op.drop_index(op.f("ix_model_versions_dataset_id"), table_name="model_versions")
    op.drop_index(op.f("ix_model_versions_workspace_id"), table_name="model_versions")

    op.drop_constraint("fk_model_versions_job_id", "model_versions", type_="foreignkey")
    op.drop_constraint("fk_model_versions_dataset_id", "model_versions", type_="foreignkey")
    op.drop_constraint("fk_model_versions_workspace_id", "model_versions", type_="foreignkey")

    op.drop_column("model_versions", "hyperparameters_json")
    op.drop_column("model_versions", "metrics_json")
    op.drop_column("model_versions", "job_id")
    op.drop_column("model_versions", "dataset_id")
    op.drop_column("model_versions", "workspace_id")
