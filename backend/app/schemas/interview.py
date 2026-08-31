"""Interview API schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.question import GeneratedQuestion, QuestionDifficulty
from app.schemas.resume import CandidateProfile


class ResumeCreateRequest(BaseModel):
    """Request body for storing a processed resume."""

    candidate_id: str
    profile: CandidateProfile


class ResumeCreateResponse(BaseModel):
    """Stored resume identifiers."""

    resume_id: str
    candidate_id: str
    claim_ids: list[str] = Field(default_factory=list)


class InterviewStartRequest(BaseModel):
    """Request body for starting a persisted interview."""

    objective: str = Field(..., min_length=1)
    difficulty: QuestionDifficulty = "medium"
    candidate_id: str | None = None
    resume_id: str | None = None
    candidate_profile: CandidateProfile | None = None


class InterviewQuestionResponse(BaseModel):
    """Question response for a persisted interview."""

    interview_id: str
    candidate_id: str
    resume_id: str | None = None
    difficulty: QuestionDifficulty
    turn_id: str
    question: GeneratedQuestion


class InterviewAnswerRequest(BaseModel):
    """Request body for submitting an interview answer."""

    turn_id: str
    answer: str = Field(..., min_length=1)


class AnsweredTurnResponse(BaseModel):
    """Persisted turn answered by the latest submission."""

    turn_id: str
    turn_number: int
    question: GeneratedQuestion
    answer: str


class InterviewAnswerResponse(BaseModel):
    """Complete result of one text interview answer submission."""

    interview_id: str
    answered_turn: AnsweredTurnResponse
    answer_analysis: AnswerAnalysis
    evaluation: AnswerEvaluation
    interviewer_decision: InterviewDecision
    next_turn_id: str
    next_question: GeneratedQuestion
    difficulty: QuestionDifficulty
    knowledge_state: CandidateKnowledgeState


class InterviewStateResponse(BaseModel):
    """Stored interview state reconstructed from persistence."""

    interview_id: str
    candidate_id: str
    resume_id: str | None = None
    objective: str
    difficulty: QuestionDifficulty
    current_question: GeneratedQuestion | None = None
    knowledge_state: dict[str, Any]
    turns: list[dict[str, Any]]
