from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class StoredDocument(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("status IN ('uploaded','processing','ready','failed')"),
        CheckConstraint("attempts BETWEEN 0 AND 3"),
        Index("ix_documents_hash_created", "content_hash", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(64))
    duplicate_of: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    page_count: Mapped[int | None] = mapped_column(Integer)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    error: Mapped[dict | None] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("platform_jobs.id"))
    processing_token: Mapped[UUID | None]


class StoredSourceUnit(Base):
    __tablename__ = "document_source_units"
    __table_args__ = (CheckConstraint("ordinal >= 0"), UniqueConstraint("document_id", "ordinal"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    sheet: Mapped[str | None] = mapped_column(String(255))
    cell: Mapped[str | None] = mapped_column(String(32))
