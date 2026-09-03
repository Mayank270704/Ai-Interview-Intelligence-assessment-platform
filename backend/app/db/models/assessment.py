"""Final interview assessment model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONColumn, created_at_column, id_column


class InterviewAssessment(Base):
    """The persisted final assessment for one completed interview."""

    __tablename__ = "interview_assessments"
    # One assessment per interview. Declared as a named constraint (matching
    # migration 0003) rather than unique=True, so the model and the deployed
    # schema agree -- the constraint's own unique index also serves the
    # interview_id lookup, so no second index is declared.
    __table_args__ = (
        UniqueConstraint("interview_id", name="uq_interview_assessments_interview_id"),
    )

    id: Mapped[str] = id_column()
    interview_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interviews.id", ondelete="CASCADE")
    )
    overall_score: Mapped[int] = mapped_column(Integer)
    technical_knowledge: Mapped[int] = mapped_column(Integer)
    knowledge_depth: Mapped[int] = mapped_column(Integer)
    problem_solving: Mapped[int] = mapped_column(Integer)
    communication: Mapped[int] = mapped_column(Integer)
    resume_claim_accuracy: Mapped[Optional[int]] = mapped_column(Integer)
    strengths: Mapped[list[Any]] = mapped_column(JSONColumn)
    weaknesses: Mapped[list[Any]] = mapped_column(JSONColumn)
    summary: Mapped[str] = mapped_column(Text)
    turns_assessed: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()
