from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class ImportedForm(Base):
    __tablename__ = "profile_forms"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    snapshot: Mapped[dict] = mapped_column(JSONB)


class ProfileHead(Base):
    __tablename__ = "profile_heads"
    __table_args__ = (CheckConstraint("latest_version >= 1"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    latest_version: Mapped[int] = mapped_column(Integer)


class ProfileVersion(Base):
    __tablename__ = "profile_versions"
    __table_args__ = (CheckConstraint("version >= 1"),)

    profile_id: Mapped[UUID] = mapped_column(ForeignKey("profile_heads.id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[UUID] = mapped_column(ForeignKey("profile_forms.id"), index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
