"""add versioned risk assessments

Revision ID: 20260914_0003
Revises: 20260914_0002
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0003"
down_revision: str | None = "20260914_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("preprocessing_version", sa.String(length=80), nullable=False),
        sa.Column("prediction_horizon_days", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(precision=12, scale=10), nullable=False),
        sa.Column("score_type", sa.String(length=80), nullable=False),
        sa.Column("calibrated", sa.Boolean(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_risk_assessments_score_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "request_id", name="uq_risk_assessments_user_request"),
    )
    op.create_index(
        "ix_risk_assessments_user_created",
        "risk_assessments",
        ["user_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_risk_assessments_user_created", table_name="risk_assessments")
    op.drop_table("risk_assessments")
