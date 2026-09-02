"""Resume model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONColumn, created_at_column, id_column


class Resume(Base):
    """A processed resume and the candidate profile extracted from it."""

    __tablename__ = "resumes"

    id: Mapped[str] = id_column()
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    profile: Mapped[dict[str, Any]] = mapped_column(JSONColumn)
    storage_path: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = created_at_column()

    candidate: Mapped["Candidate"] = relationship(back_populates="resumes")  # noqa: F821
    claims: Mapped[list["ResumeClaim"]] = relationship(  # noqa: F821
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeClaim.created_at",
    )
