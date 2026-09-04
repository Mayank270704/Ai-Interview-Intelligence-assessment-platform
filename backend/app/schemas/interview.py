"""Interview API schemas."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.question import GeneratedQuestion, QuestionDifficulty
from app.schemas.resume import CandidateProfile

InterviewStatus = Literal["created", "in_progress", "completed"]

# Whitespace is not content. Stripping before the length check keeps a blank
# objective or answer out of the pipeline entirely, rather than letting it reach
# a service that would either raise or spend a model call analysing nothing.
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ResumeCreateRequest(BaseModel):
    """Request body for storing a processed resume."""

    candidate_id: str
    profile: CandidateProfile


class ResumeCreateResponse(BaseModel):
    """Stored resume identifiers."""

    resume_id: str
    candidate_id: str
    claim_ids: list[str] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    """Stored resume identifiers and the profile extracted from an uploaded PDF."""

    resume_id: str
    candidate_id: str
    profile: CandidateProfile


class InterviewStartRequest(BaseModel):
    """Request body for starting a persisted interview."""

    objective: NonBlankText
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
    status: InterviewStatus
    turn_id: str
    question: GeneratedQuestion


class InterviewAnswerRequest(BaseModel):
    """Request body for submitting an interview answer."""

    turn_id: str
    answer: NonBlankText


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
    status: InterviewStatus
    knowledge_state: CandidateKnowledgeState


class InterviewTurnResponse(BaseModel):
    """One persisted interview turn and everything the pipeline derived from it."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    turn_number: int
    question: GeneratedQuestion
    answer: str | None = None
    answer_analysis: AnswerAnalysis | None = None
    evaluation: AnswerEvaluation | None = None
    decision: InterviewDecision | None = None
    knowledge_state: CandidateKnowledgeState | None = None
    pending_claim_ids: list[str] | None = None
    created_at: datetime


class InterviewStateResponse(BaseModel):
    """Stored interview state reconstructed from persistence."""

    interview_id: str
    candidate_id: str
    resume_id: str | None = None
    objective: str
    difficulty: QuestionDifficulty
    status: InterviewStatus
    current_question: GeneratedQuestion | None = None
    knowledge_state: CandidateKnowledgeState
    turns: list[InterviewTurnResponse]
