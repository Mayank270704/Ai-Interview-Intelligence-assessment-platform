"""Answer analysis schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class ResumeClaimRelationship(BaseModel):
    """Relationship between the answer and a relevant resume claim."""

    claim_text: str = Field(
        ..., description="The resume claim being related to the answer"
    )
    relationship: str = Field(
        ...,
        description="How the answer relates to the claim (supports, contradicts, clarifies, or unrelated)",
    )
    evidence: Optional[str] = Field(
        None,
        description="Evidence from the answer or resume that supports the relationship",
    )


class ConceptEvidence(BaseModel):
    """Evidence from the answer that relates to one specific concept."""

    concept: str = Field(
        ..., description="The concept this evidence relates to"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence from the answer that supports, contradicts, or leaves this concept unresolved",
    )


class AnswerAnalysis(BaseModel):
    """Structured analysis of a candidate answer for interview planning."""

    technical_correctness: str = Field(
        ...,
        description="Assessment of technical correctness: correct, partially_correct, incorrect, or unknown",
    )
    demonstrated_concepts: list[str] = Field(
        default_factory=list, description="Concepts the candidate clearly demonstrated"
    )
    missing_concepts: list[str] = Field(
        default_factory=list, description="Concepts that were missing or not addressed"
    )
    incorrect_concepts: list[str] = Field(
        default_factory=list,
        description="Concepts that appear incorrect or misunderstood",
    )
    reasoning_quality: str = Field(
        ...,
        description="Overall reasoning quality: strong, adequate, weak, or unclear",
    )
    answer_relevance: str = Field(
        ...,
        description="How relevant the answer is to the question: high, medium, low, or off_topic",
    )
    technical_depth: str = Field(
        ...,
        description="Depth of technical explanation: shallow, moderate, deep, or insufficient",
    )
    completeness: str = Field(
        ...,
        description="Completeness assessment: complete, partial, incomplete, or vague",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims made by the candidate that lack support or evidence",
    )
    resume_claim_relationships: list[ResumeClaimRelationship] = Field(
        default_factory=list,
        description="Relationship between the answer and any relevant resume claims",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended next interviewer actions, e.g., probe_deeper, clarify, challenge, increase_difficulty, decrease_difficulty, change_topic, investigate_resume_claim, conclude_topic",
    )
    concept_evidence: list[ConceptEvidence] = Field(
        default_factory=list,
        description="Evidence grouped by the concept it relates to, covering demonstrated, missing, and incorrect concepts",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence used to support the assessment, grounded in the answer, profile, and context",
    )