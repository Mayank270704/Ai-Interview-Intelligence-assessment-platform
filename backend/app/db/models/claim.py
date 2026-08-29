"""Claim model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_column, id_column


class ResumeClaim(Base):
    """A resume claim that can be investigated during an interview."""

    __tablename__ = "resume_claims"

    id: Mapped[str] = id_column()
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    claim_text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    context: Mapped[Optional[str]] = mapped_column(Text)
    resume_evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    resume: Mapped["Resume"] = relationship(back_populates="claims")  # noqa: F821
