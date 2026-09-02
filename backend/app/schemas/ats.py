"""ATS resume score schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ATSMode = Literal["readiness", "jd_match"]


class ATSScoreRequest(BaseModel):
    """Request body for scoring an existing resume, with an optional job description."""

    job_description: str | None = Field(
        None,
        description="Optional job description text. Omit or leave blank for a "
        "resume-readiness score instead of job-specific compatibility.",
    )


class ATSDiagnostic(BaseModel):
    """One structured, deterministic diagnostic finding about the resume."""

    model_config = ConfigDict(from_attributes=True)

    type: str
    section: str
    affected_text: str | None = None
    explanation: str
    actionable_fix: str


class ATSScoreResponse(BaseModel):
    """Deterministic ATS score and supporting evidence for one resume."""

    resume_id: str
    ats_score: int = Field(..., ge=0, le=100)
    mode: ATSMode
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    section_feedback: list[str] = Field(default_factory=list)
    experience_feedback: list[str] = Field(default_factory=list)
    project_feedback: list[str] = Field(default_factory=list)
    measurable_impact_feedback: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    diagnostics: list[ATSDiagnostic] = Field(default_factory=list)
