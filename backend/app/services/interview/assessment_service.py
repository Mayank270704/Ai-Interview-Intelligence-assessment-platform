"""Final interview assessment orchestration: gathers turn evidence and scores it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.assessment.generator import FinalAssessmentGenerator
from app.db.repositories import interview_repository
from app.schemas.assessment import FinalAssessment
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.knowledge_state import CandidateKnowledgeState

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def build_final_assessment(session: "Session", interview_id: str, objective: str) -> FinalAssessment:
    """Aggregate a completed interview's answered turns into a final assessment.

    Reads directly from the persisted turn evidence (each turn's stored AnswerEvaluation,
    and the last answered turn's accumulated knowledge state) rather than reconstructing
    the interview turn pipeline, since assessment is a read-only aggregation, not an
    interview-turn operation.
    """
    turns = interview_repository.get_turns(session, interview_id)
    answered = [turn for turn in turns if turn.answer is not None and turn.evaluation is not None]
    if not answered:
        raise ValueError("The interview has no answered turns with evaluation data to assess.")

    evaluations = [AnswerEvaluation.model_validate(turn.evaluation) for turn in answered]
    last_knowledge_state = answered[-1].knowledge_state
    knowledge_state = (
        CandidateKnowledgeState.model_validate(last_knowledge_state) if last_knowledge_state else None
    )

    return FinalAssessmentGenerator().generate(
        interview_id=interview_id,
        objective=objective,
        evaluations=evaluations,
        knowledge_state=knowledge_state,
    )
