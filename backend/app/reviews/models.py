from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class ReviewRecord(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("revision >= 0"),
        CheckConstraint("status IN ('draft', 'confirmed')"),
        CheckConstraint("(status = 'confirmed') = (confirmed_at IS NOT NULL)"),
    )
    extraction_id: Mapped[UUID] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    extraction_snapshot: Mapped[dict] = mapped_column(JSONB)
    profile_snapshot: Mapped[dict] = mapped_column(JSONB)
    form_snapshot: Mapped[dict] = mapped_column(JSONB)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewRevision(Base):
    __tablename__ = "review_revisions"
    extraction_id: Mapped[UUID] = mapped_column(
        ForeignKey("reviews.extraction_id"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
