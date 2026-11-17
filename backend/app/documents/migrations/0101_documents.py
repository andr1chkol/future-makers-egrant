"""Private documents and immutable source units. Register this version location in Alembic."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0101_documents"
down_revision = "0001_platform"
branch_labels = ("documents",)
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("duplicate_of", sa.Uuid(), sa.ForeignKey("documents.id")),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("page_count", sa.Integer()),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("error", postgresql.JSONB()),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("platform_jobs.id")),
        sa.Column("processing_token", sa.Uuid()),
        sa.CheckConstraint("status IN ('uploaded','processing','ready','failed')"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3"),
    )
    op.create_index("ix_documents_hash_created", "documents", ["content_hash", "created_at"])
    op.create_table(
        "document_source_units",
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), primary_key=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("sheet", sa.String(255)),
        sa.Column("cell", sa.String(32)),
        sa.CheckConstraint("ordinal >= 0"),
        sa.UniqueConstraint("document_id", "ordinal"),
    )


def downgrade():
    op.drop_table("document_source_units")
    op.drop_table("documents")
