from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class SubmissionRecord(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("mode IN ('export', 'egrant')"),
        CheckConstraint(
            "status IN ('prepared', 'exported', 'applying', 'applied', 'failed', 'unknown')"
        ),
        CheckConstraint("review_revision >= 1"),
        Index("ix_submissions_apply_recovery", "mode", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    review_id: Mapped[UUID]
    review_revision: Mapped[int]
    mode: Mapped[str] = mapped_column(String(16))
    target_context: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSONB)
    external_receipt: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
