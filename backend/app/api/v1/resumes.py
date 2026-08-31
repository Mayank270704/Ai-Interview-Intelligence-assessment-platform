"""Resume API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.db.repositories import candidate_repository, resume_repository
from app.schemas.interview import ResumeCreateRequest, ResumeCreateResponse

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeCreateResponse)
def create_resume(
    request: ResumeCreateRequest,
    session: Session = Depends(get_session),
) -> ResumeCreateResponse:
    if candidate_repository.get_candidate(session, request.candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    resume = resume_repository.create_resume(
        session,
        candidate_id=request.candidate_id,
        profile=request.profile,
    )
    profile = resume_repository.load_candidate_profile(session, resume.id)
    return ResumeCreateResponse(
        resume_id=resume.id,
        candidate_id=resume.candidate_id,
        claim_ids=[claim.claim_id for claim in profile.claims if claim.claim_id]
        if profile
        else [],
    )
