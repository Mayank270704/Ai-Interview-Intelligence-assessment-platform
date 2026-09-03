"""Candidate API schemas."""

from pydantic import BaseModel, Field


class CandidateCreate(BaseModel):
    """Request body for creating a candidate."""

    full_name: str | None = None
    email: str | None = None
    ml_training_consent: bool = Field(
        default=False,
        description=(
            "Opt in to this candidate's structured interview signals being used for "
            "offline model training. Defaults to false; consent is never assumed."
        ),
    )


class CandidateRead(BaseModel):
    """Persisted candidate response."""

    id: str
    full_name: str | None = None
    email: str | None = None
    ml_training_consent: bool = False
