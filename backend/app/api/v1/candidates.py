"""Candidate API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.db.repositories import candidate_repository
from app.db.supabase_auth import AuthenticatedUser
from app.schemas.candidate import CandidateCreate, CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateRead)
def create_candidate(
    request: CandidateCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CandidateRead:
    candidate = candidate_repository.create_candidate(
        session,
        full_name=request.full_name,
        email=request.email,
        owner_user_id=current_user.id,
    )
    return CandidateRead(
        id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
    )
