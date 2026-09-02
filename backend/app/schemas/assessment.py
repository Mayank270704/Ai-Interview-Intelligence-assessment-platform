"""Final interview assessment schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FinalAssessment(BaseModel):
    """Evidence-based assessment aggregated from a completed interview's turns."""

    model_config = ConfigDict(from_attributes=True)

    interview_id: str
    overall_score: int = Field(..., ge=0, le=100)
    technical_knowledge: int = Field(..., ge=0, le=100)
    knowledge_depth: int = Field(..., ge=0, le=100)
    problem_solving: int = Field(..., ge=0, le=100)
    communication: int = Field(..., ge=0, le=100)
    resume_claim_accuracy: int | None = Field(None, ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    summary: str
    turns_assessed: int = Field(..., ge=0)
    created_at: datetime | None = None
