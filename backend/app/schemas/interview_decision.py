"""Schemas for interview decision-making and strategy."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

InterviewerActionType = Literal[
    "DEEPEN",
    "CLARIFY",
    "CHALLENGE",
    "INCREASE_DIFFICULTY",
    "DECREASE_DIFFICULTY",
    "INVESTIGATE_CLAIM",
    "EXPLORE_RELATED_CONCEPT",
    "CHANGE_TOPIC",
    "CONCLUDE_TOPIC",
]

DifficultyDirection = Literal["increase", "decrease", "maintain"]


class InterviewDecision(BaseModel):
    """Structured decision made by the Interviewer Brain."""

    action: InterviewerActionType = Field(
        ..., description="The next interview action to take"
    )
    target_concept: str = Field(
        ..., description="The primary concept or topic being targeted"
    )
    reasoning: str = Field(
        ...,
        description="Evidence-based reasoning for this decision",
    )
    reasoning_evidence: list[str] = Field(
        default_factory=list,
        description="Specific evidence from candidate response, profile, or state supporting the decision",
    )
    difficulty_direction: DifficultyDirection = Field(
        default="maintain",
        description="Whether to increase, decrease, or maintain interview difficulty",
    )
    next_topic: Optional[str] = Field(
        None,
        description="If CHANGE_TOPIC or EXPLORE_RELATED_CONCEPT, the target topic or concept",
    )
    resume_claim_to_investigate: Optional[str] = Field(
        None,
        description="If INVESTIGATE_CLAIM, the specific resume claim to verify",
    )
    should_probe_further: bool = Field(
        default=True,
        description="Whether the interviewer should continue probing the current topic or move on",
    )
    confidence: Literal["low", "medium", "high"] = Field(
        ..., description="Confidence in this decision based on available evidence"
    )


class InterviewStrategy(BaseModel):
    """Interview strategy context for decision-making."""

    interview_id: str = Field(..., description="Unique interview identifier")
    current_topic: str = Field(..., description="The topic currently being explored")
    explored_concepts: list[str] = Field(
        default_factory=list, description="Concepts already thoroughly explored"
    )
    pending_claims: list[str] = Field(
        default_factory=list,
        description="Resume claims that still need to be verified or investigated",
    )
    unresolved_gaps: list[str] = Field(
        default_factory=list,
        description="Significant knowledge gaps that need clarification",
    )
    question_count: int = Field(
        default=0, description="Number of questions asked so far"
    )
    estimated_interview_depth: Literal["shallow", "moderate", "deep"] = Field(
        default="moderate", description="Estimated depth of the interview so far"
    )
