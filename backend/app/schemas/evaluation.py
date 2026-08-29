"""Evaluation schemas."""

from pydantic import BaseModel, Field


class AnswerEvaluation(BaseModel):
    """Structured evaluation of a candidate answer using available evidence."""

    technical_correctness: str = Field(
        ..., description="Overall technical correctness: strong, moderate, weak, or partial"
    )
    conceptual_understanding: str = Field(
        ..., description="Conceptual understanding: strong, moderate, weak, or limited"
    )
    completeness: str = Field(
        ..., description="Completeness of the answer: complete, partial, incomplete, or vague"
    )
    technical_depth: str = Field(
        ..., description="Technical depth: deep, moderate, shallow, or limited"
    )
    reasoning_quality: str = Field(
        ..., description="Reasoning quality: strong, moderate, weak, or limited"
    )
    relevance: str = Field(
        ..., description="Relevance to the question: high, medium, low, or off_topic"
    )
    application_ability: str = Field(
        ..., description="Ability to apply concepts in practice: strong, moderate, limited, or weak"
    )
    confidence: str = Field(
        ..., description="Confidence in this assessment based on the evidence available: low, medium, or high"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting the assessment, grounded in the answer and context",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Important missing concepts or incomplete areas supported by the evidence",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Strong points supported by the answer",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims without sufficient support",
    )
    uncertainty_notes: list[str] = Field(
        default_factory=list,
        description="Notes describing uncertainty or the limits of the current evidence",
    )