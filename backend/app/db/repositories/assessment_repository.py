"""Final interview assessment repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InterviewAssessment
from app.schemas.assessment import FinalAssessment


def get_assessment(session: Session, interview_id: str) -> InterviewAssessment | None:
    """Load the persisted final assessment for an interview, if one exists."""
    statement = select(InterviewAssessment).where(InterviewAssessment.interview_id == interview_id)
    return session.scalars(statement).first()


def create_assessment(
    session: Session,
    interview_id: str,
    assessment: FinalAssessment,
) -> InterviewAssessment:
    """Persist a newly generated final assessment for an interview."""
    row = InterviewAssessment(
        interview_id=interview_id,
        overall_score=assessment.overall_score,
        technical_knowledge=assessment.technical_knowledge,
        knowledge_depth=assessment.knowledge_depth,
        problem_solving=assessment.problem_solving,
        communication=assessment.communication,
        resume_claim_accuracy=assessment.resume_claim_accuracy,
        strengths=list(assessment.strengths),
        weaknesses=list(assessment.weaknesses),
        summary=assessment.summary,
        turns_assessed=assessment.turns_assessed,
    )
    session.add(row)
    session.flush()
    return row
