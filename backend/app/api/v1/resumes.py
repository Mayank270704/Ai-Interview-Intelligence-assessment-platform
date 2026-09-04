"""Resume API routes."""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.ats.scorer import InvalidJobDescriptionError, score_resume
from app.ai.resume_intelligence.pdf_processor import PDFExtractionError
from app.ai.resume_intelligence.processor import ResumeProcessor
from app.core.security import ensure_owner, get_current_user
from app.db import storage as resume_storage
from app.db.base import new_id
from app.db.database import get_session
from app.db.repositories import candidate_repository, resume_repository
from app.db.supabase_auth import AuthenticatedUser
from app.schemas.ats import ATSScoreRequest, ATSScoreResponse
from app.schemas.interview import (
    ResumeCreateRequest,
    ResumeCreateResponse,
    ResumeUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_RESUME_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"


@router.post("", response_model=ResumeCreateResponse)
def create_resume(
    request: ResumeCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResumeCreateResponse:
    candidate = candidate_repository.get_candidate(session, request.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    ensure_owner(candidate.owner_user_id, current_user)

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


@router.post("/upload", response_model=ResumeUploadResponse)
def upload_resume(
    file: UploadFile = File(...),
    candidate_id: str | None = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResumeUploadResponse:
    if candidate_id is not None:
        candidate = candidate_repository.get_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        ensure_owner(candidate.owner_user_id, current_user)

    pdf_bytes = file.file.read(MAX_RESUME_UPLOAD_BYTES + 1)
    if not pdf_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(pdf_bytes) > MAX_RESUME_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")
    if not pdf_bytes.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(status_code=415, detail="Uploaded file must be a PDF")

    # Checked before the analysis, not after: the upload cannot succeed without
    # somewhere to put the file, and analysis is the expensive step of this
    # request. Failing here also keeps a missing-configuration error from being
    # reported as an upstream storage outage further down.
    if not resume_storage.is_configured():
        logger.error(
            "Resume upload rejected: Supabase Storage is not configured "
            "(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)."
        )
        raise HTTPException(
            status_code=503, detail="Resume storage is not configured on this server"
        )

    try:
        profile = ResumeProcessor().process_resume(pdf_bytes)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        # The provider's own message can carry upstream detail the caller has no
        # use for, so it goes to the server log and the caller gets the status.
        logger.warning("Resume analysis failed: %s", exc)
        raise HTTPException(
            status_code=502, detail="Could not analyze the resume right now"
        ) from exc

    if candidate_id is None:
        candidate = candidate_repository.create_candidate(
            session,
            full_name=profile.identity.full_name,
            email=profile.identity.email,
            owner_user_id=current_user.id,
        )
        candidate_id = candidate.id

    resume_id = new_id()
    storage_path = resume_storage.resume_storage_path(candidate_id, resume_id)
    try:
        resume_storage.upload_resume_pdf(storage_path, pdf_bytes)
    except resume_storage.StorageUploadError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to store the uploaded resume file"
        ) from exc

    # The PDF is in the bucket from here on, but the row that references it is
    # still uncommitted. If persisting fails, the request transaction rolls back
    # and nothing would point at the object, so remove it rather than orphan it.
    try:
        resume = resume_repository.create_resume(
            session,
            candidate_id,
            profile,
            resume_id=resume_id,
            storage_path=storage_path,
        )
        stored_profile = resume_repository.load_candidate_profile(session, resume.id)
    except Exception:
        resume_storage.delete_resume_pdf(storage_path)
        raise

    return ResumeUploadResponse(
        resume_id=resume.id,
        candidate_id=resume.candidate_id,
        profile=stored_profile,
    )


@router.post("/{resume_id}/ats-score", response_model=ATSScoreResponse)
def get_ats_score(
    resume_id: str,
    request: ATSScoreRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ATSScoreResponse:
    resume = resume_repository.get_resume(session, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    ensure_owner(resume.candidate.owner_user_id, current_user)

    profile = resume_repository.load_candidate_profile(session, resume_id)

    try:
        result = score_resume(profile, request.job_description)
    except InvalidJobDescriptionError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return ATSScoreResponse(resume_id=resume_id, **result.__dict__)
