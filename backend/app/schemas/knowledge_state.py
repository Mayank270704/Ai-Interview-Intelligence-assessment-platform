"""Schemas for candidate knowledge state and claim verification."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.resume import claim_identity

ConfidenceLevel = Literal["low", "medium", "high"]
ClaimVerificationStatus = Literal["supported", "unsupported", "uncertain"]


class ConceptState(BaseModel):
    """Current estimate of a candidate's knowledge for one concept."""

    concept: str = Field(..., description="Concept, skill, or topic under assessment")
    confidence: ConfidenceLevel = Field(
        default="low",
        description="Confidence in the current understanding of this concept",
    )
    demonstrated: bool = Field(
        default=False, description="Whether the candidate has demonstrated the concept"
    )
    missing: bool = Field(
        default=False, description="Whether the concept remains under-evidenced"
    )
    incorrect: bool = Field(
        default=False, description="Whether the concept appears to be misunderstood"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Interview evidence used to estimate the concept state",
    )


class ClaimVerification(BaseModel):
    """Result of verifying a resume claim using observed interview evidence."""

    claim_id: Optional[str] = Field(
        None, description="Stable identifier of the resume claim, when it has been persisted"
    )
    claim_text: str = Field(..., description="The claim being checked")
    status: ClaimVerificationStatus = Field(
        ...,
        description="Whether the claim is supported, unsupported, or remains uncertain",
    )
    confidence: ConfidenceLevel = Field(
        ..., description="Confidence in the verification result"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence used to validate or challenge the claim",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Additional context about how the claim was evaluated",
    )

    @property
    def identity(self) -> str:
        """The stable identity of the resume claim this verification belongs to."""
        return claim_identity(self.claim_id, self.claim_text)


class CandidateKnowledgeState(BaseModel):
    """Evidence-based estimate of candidate knowledge across interview topics."""

    concept_states: list[ConceptState] = Field(
        default_factory=list,
        description="Estimated state for each discussed concept or topic",
    )
    claim_verifications: list[ClaimVerification] = Field(
        default_factory=list,
        description="Verification status for each resume claim investigated",
    )
    summary: str = Field(
        default="",
        description="Concise summary of the candidate's current knowledge state",
    )
