"""Candidate API schemas."""

from pydantic import BaseModel


class CandidateCreate(BaseModel):
    """Request body for creating a candidate."""

    full_name: str | None = None
    email: str | None = None


class CandidateRead(BaseModel):
    """Persisted candidate response."""

    id: str
    full_name: str | None = None
    email: str | None = None
