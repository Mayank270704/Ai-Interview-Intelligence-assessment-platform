"""Candidate model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_column, id_column


class Candidate(Base):
    """A person being interviewed."""

    __tablename__ = "candidates"

    id: Mapped[str] = id_column()
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = created_at_column()

    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        back_populates="candidate", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(  # noqa: F821
        back_populates="candidate", cascade="all, delete-orphan"
    )
