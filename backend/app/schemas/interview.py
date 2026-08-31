"""Interview API schemas."""

from typing import Any

from pydantic import BaseModel, Field

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
    question: GeneratedQuestion


class InterviewAnswerRequest(BaseModel):
    """Request body for submitting an interview answer."""

    answer: str = Field(..., min_length=1)


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
