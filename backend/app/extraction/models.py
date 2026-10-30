from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class ExtractionRecord(Base):
    __tablename__ = "extractions"
    __table_args__ = (
        CheckConstraint("status IN ('queued','running','ready','failed')"),
        CheckConstraint("mode IN ('live','fixture')"),
        CheckConstraint("attempt >= 0 AND profile_version >= 1"),
        CheckConstraint("status <> 'running' OR run_token IS NOT NULL"),
        Index("ix_extractions_created", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(index=True)
    profile_id: Mapped[UUID]
    profile_version: Mapped[int] = mapped_column(Integer)
    # Frozen copy of the profile and the form's option keys at creation time;
    # later profile versions or form edits never change how this run is read.
    profile_snapshot: Mapped[dict] = mapped_column(JSONB)
    option_keys: Mapped[dict] = mapped_column(JSONB)
    mode: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    # Fences writes from a worker whose lease was reclaimed while it waited on the provider.
    run_token: Mapped[UUID | None]
    fields: Mapped[list] = mapped_column(JSONB, default=list)
    tables: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    error: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
