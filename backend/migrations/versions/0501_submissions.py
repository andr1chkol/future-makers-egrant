"""Persist immutable confirmed exports and idempotency intent."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0501_submissions"
down_revision = "0001_platform"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("review_revision", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("target_context", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("external_receipt", postgresql.JSONB(), nullable=True),
        sa.Column("error", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("mode IN ('export', 'egrant')"),
        sa.CheckConstraint(
            "status IN ('prepared', 'exported', 'applying', 'applied', 'failed', 'unknown')"
        ),
        sa.CheckConstraint("review_revision >= 1"),
    )
    op.create_index("ix_submissions_apply_recovery", "submissions", ["mode", "status"])


def downgrade():
    op.drop_table("submissions")
