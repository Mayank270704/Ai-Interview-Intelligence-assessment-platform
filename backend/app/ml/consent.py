"""Which interview turns may legitimately become training data.

Eligibility is opt-in and checked at export time rather than at write time: the
interview tables record what happened, and consent decides only what may leave
them. A candidate who never opted in contributes nothing, and withdrawing
consent immediately makes their turns ineligible for the next export.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Candidate, Interview, InterviewTurn


def candidate_is_eligible(candidate: Candidate | None) -> bool:
    """True only for a candidate who explicitly opted in."""
    return bool(candidate is not None and candidate.ml_training_consent)


def eligible_turns(session: Session, *, interview_id: str | None = None) -> list[InterviewTurn]:
    """Load answered turns whose candidate consented to training-data use.

    Ordered by interview and turn number so an export is byte-identical across
    runs against unchanged data.
    """
    statement = (
        select(InterviewTurn)
        .join(Interview, Interview.id == InterviewTurn.interview_id)
        .join(Candidate, Candidate.id == Interview.candidate_id)
        .where(Candidate.ml_training_consent.is_(True))
        .where(InterviewTurn.answer.is_not(None))
        .order_by(InterviewTurn.interview_id, InterviewTurn.turn_number)
    )
    if interview_id is not None:
        statement = statement.where(InterviewTurn.interview_id == interview_id)
    return list(session.scalars(statement))
