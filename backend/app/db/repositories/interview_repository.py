"""Interview repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Interview, InterviewTurn
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.question import GeneratedQuestion


def create_interview(
    session: Session,
    candidate_id: str,
    objective: str,
    difficulty: str,
    resume_id: str | None = None,
) -> Interview:
    """Create an interview row."""
    interview = Interview(
        candidate_id=candidate_id,
        resume_id=resume_id,
        objective=objective,
        difficulty=difficulty,
    )
    session.add(interview)
    session.flush()
    return interview


def get_interview(session: Session, interview_id: str) -> Interview | None:
    """Load an interview by id."""
    return session.get(Interview, interview_id)


def get_turn(session: Session, turn_id: str) -> InterviewTurn | None:
    """Load one interview turn by id."""
    return session.get(InterviewTurn, turn_id)


def update_interview_difficulty(
    session: Session,
    interview_id: str,
    difficulty: str,
) -> Interview:
    """Persist the interview's current adaptive difficulty."""
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise ValueError(f"Interview {interview_id} was not found.")
    interview.difficulty = difficulty
    session.flush()
    return interview


def get_turns(session: Session, interview_id: str) -> list[InterviewTurn]:
    """Load an interview's turns in the order they were asked."""
    statement = (
        select(InterviewTurn)
        .where(InterviewTurn.interview_id == interview_id)
        .order_by(InterviewTurn.turn_number)
    )
    return list(session.scalars(statement))


def add_question_turn(
    session: Session,
    interview_id: str,
    question: GeneratedQuestion,
) -> InterviewTurn:
    """Record a newly asked question as the next turn of the interview."""
    turn = InterviewTurn(
        interview_id=interview_id,
        turn_number=len(get_turns(session, interview_id)) + 1,
        question=question.model_dump(mode="json"),
    )
    session.add(turn)
    session.flush()
    return turn


def record_answer(
    session: Session,
    turn: InterviewTurn,
    answer: str,
    answer_analysis: AnswerAnalysis,
    evaluation: AnswerEvaluation,
    decision: InterviewDecision,
    knowledge_state: CandidateKnowledgeState,
    pending_claim_ids: list[str],
) -> InterviewTurn:
    """Store the answer to a turn together with everything derived from it."""
    turn.answer = answer
    turn.answer_analysis = answer_analysis.model_dump(mode="json")
    turn.evaluation = evaluation.model_dump(mode="json")
    turn.decision = decision.model_dump(mode="json")
    turn.knowledge_state = knowledge_state.model_dump(mode="json")
    turn.pending_claim_ids = list(pending_claim_ids)
    session.flush()
    return turn
