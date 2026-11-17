"""Separate editable snapshots, frozen context and immutable revision history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0401_reviews"
down_revision = "0001_platform"
branch_labels = ("reviews",)
depends_on = None


def upgrade():
    op.create_table(
        "reviews",
        sa.Column("extraction_id", sa.Uuid(), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("extraction_snapshot", JSONB(), nullable=False),
        sa.Column("profile_snapshot", JSONB(), nullable=False),
        sa.Column("form_snapshot", JSONB(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("revision >= 0"),
        sa.CheckConstraint("status IN ('draft', 'confirmed')"),
        sa.CheckConstraint("(status = 'confirmed') = (confirmed_at IS NOT NULL)"),
    )
    op.create_table(
        "review_revisions",
        sa.Column(
            "extraction_id", sa.Uuid(), sa.ForeignKey("reviews.extraction_id"), primary_key=True
        ),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    op.drop_table("review_revisions")
    op.drop_table("reviews")
