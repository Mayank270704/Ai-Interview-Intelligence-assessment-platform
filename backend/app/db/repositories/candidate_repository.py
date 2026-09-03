"""Candidate repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Candidate


def create_candidate(
    session: Session,
    full_name: str | None = None,
    email: str | None = None,
    owner_user_id: str | None = None,
    ml_training_consent: bool = False,
) -> Candidate:
    """Create a candidate row, owned by the authenticated user who created it."""
    candidate = Candidate(
        full_name=full_name,
        email=email,
        owner_user_id=owner_user_id,
        ml_training_consent=ml_training_consent,
    )
    session.add(candidate)
    session.flush()
    return candidate


def get_candidate(session: Session, candidate_id: str) -> Candidate | None:
    """Load a candidate by id."""
    return session.get(Candidate, candidate_id)
