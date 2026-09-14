"""Create immutable health measurements.

Revision ID: 20260914_0002
Revises: 20260913_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0002"
down_revision: str | Sequence[str] | None = "20260913_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    metric_type = postgresql.ENUM(
        "heart_rate",
        "blood_pressure",
        "weight",
        "blood_glucose",
        "sleep_duration",
        "physical_activity_duration",
        name="metric_type",
        create_type=False,
    )
    glucose_context = postgresql.ENUM(
        "fasting",
        "postprandial",
        "random",
        "unknown",
        name="glucose_context",
        create_type=False,
    )
    metric_type.create(op.get_bind(), checkfirst=True)
    glucose_context.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", metric_type, nullable=False),
        sa.Column("numeric_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("systolic", sa.Integer(), nullable=True),
        sa.Column("diastolic", sa.Integer(), nullable=True),
        sa.Column("glucose_context", glucose_context, nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "numeric_value IS NULL OR numeric_value > 0",
            name="ck_measurements_positive_numeric",
        ),
        sa.CheckConstraint(
            "systolic IS NULL OR systolic > 0", name="ck_measurements_positive_systolic"
        ),
        sa.CheckConstraint(
            "diastolic IS NULL OR diastolic > 0", name="ck_measurements_positive_diastolic"
        ),
        sa.CheckConstraint(
            "(metric = 'blood_pressure' AND numeric_value IS NULL "
            "AND systolic IS NOT NULL AND diastolic IS NOT NULL) OR "
            "(metric <> 'blood_pressure' AND numeric_value IS NOT NULL "
            "AND systolic IS NULL AND diastolic IS NULL)",
            name="ck_measurements_value_shape",
        ),
        sa.CheckConstraint(
            "(metric = 'blood_glucose' AND glucose_context IS NOT NULL) OR "
            "(metric <> 'blood_glucose' AND glucose_context IS NULL)",
            name="ck_measurements_context_shape",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_measurements_user_measured",
        "measurements",
        ["user_id", "measured_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_measurements_user_measured", table_name="measurements")
    op.drop_table("measurements")
    sa.Enum(name="glucose_context").drop(op.get_bind())
    sa.Enum(name="metric_type").drop(op.get_bind())
