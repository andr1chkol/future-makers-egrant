"""Platform sessions and durable jobs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platform_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_platform_sessions_expires_at", "platform_sessions", ["expires_at"])
    op.create_table(
        "platform_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("attempt >= 0 AND max_attempts BETWEEN 1 AND 10"),
        sa.CheckConstraint("status IN ('queued','running','done','failed')"),
        sa.CheckConstraint("kind IN ('document.process','extraction.process','submission.apply')"),
    )
    op.create_index(
        "ix_platform_jobs_claim", "platform_jobs", ["status", "available_at", "lease_until"]
    )


def downgrade():
    op.drop_table("platform_jobs")
    op.drop_table("platform_sessions")
