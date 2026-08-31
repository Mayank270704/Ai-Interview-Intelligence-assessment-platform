"""Candidate API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.db.repositories import candidate_repository
from app.schemas.candidate import CandidateCreate, CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateRead)
def create_candidate(
    request: CandidateCreate,
    session: Session = Depends(get_session),
) -> CandidateRead:
    candidate = candidate_repository.create_candidate(
        session,
        full_name=request.full_name,
        email=request.email,
    )
    return CandidateRead(
        id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
    )
