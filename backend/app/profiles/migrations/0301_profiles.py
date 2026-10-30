"""Immutable form definitions and versioned extraction profiles."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0301_profiles"
down_revision = "0001_platform"
branch_labels = ("profiles",)
depends_on = None


def upgrade():
    op.create_table(
        "profile_forms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "profile_heads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("latest_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("latest_version >= 1"),
    )
    op.create_table(
        "profile_versions",
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("profile_heads.id"), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("form_id", sa.Uuid(), sa.ForeignKey("profile_forms.id"), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("version >= 1"),
    )
    op.create_index("ix_profile_versions_form_id", "profile_versions", ["form_id"])
    op.execute("""
        CREATE FUNCTION profiles_reject_snapshot_change() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Immutable profile snapshot' USING ERRCODE = '23000';
        END;
        $$ LANGUAGE plpgsql
    """)
    for table in ("profile_forms", "profile_versions"):
        op.execute(f"""
            CREATE TRIGGER reject_snapshot_change BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION profiles_reject_snapshot_change()
        """)


def downgrade():
    op.drop_table("profile_versions")
    op.drop_table("profile_heads")
    op.drop_table("profile_forms")
    op.execute("DROP FUNCTION profiles_reject_snapshot_change()")
