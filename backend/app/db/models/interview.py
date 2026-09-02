"""Interview model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONColumn, created_at_column, id_column


class Interview(Base):
    """One interview session with a candidate."""

    __tablename__ = "interviews"

    id: Mapped[str] = id_column()
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="SET NULL")
    )
    objective: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = created_at_column()

    candidate: Mapped["Candidate"] = relationship(back_populates="interviews")  # noqa: F821
    turns: Mapped[list["InterviewTurn"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewTurn.turn_number",
    )


class InterviewTurn(Base):
    """One asked question and everything the pipeline derived from its answer."""

    __tablename__ = "interview_turns"
    __table_args__ = (UniqueConstraint("interview_id", "turn_number"),)

    id: Mapped[str] = id_column()
    interview_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    turn_number: Mapped[int] = mapped_column(Integer)
    question: Mapped[dict[str, Any]] = mapped_column(JSONColumn)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    answer_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONColumn)
    evaluation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONColumn)
    decision: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONColumn)
    knowledge_state: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONColumn)
    pending_claim_ids: Mapped[Optional[list[str]]] = mapped_column(JSONColumn)
    created_at: Mapped[datetime] = created_at_column()

    interview: Mapped["Interview"] = relationship(back_populates="turns")
