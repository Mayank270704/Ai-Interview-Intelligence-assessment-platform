"""Resume API routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.resume_intelligence.pdf_processor import PDFExtractionError
from app.ai.resume_intelligence.processor import ResumeProcessor
from app.db.database import get_session
from app.db.repositories import candidate_repository, resume_repository
from app.schemas.interview import (
    ResumeCreateRequest,
    ResumeCreateResponse,
    ResumeUploadResponse,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_RESUME_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"


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


@router.post("/upload", response_model=ResumeUploadResponse)
def upload_resume(
    file: UploadFile = File(...),
    candidate_id: str | None = Form(None),
    session: Session = Depends(get_session),
) -> ResumeUploadResponse:
    if candidate_id is not None and candidate_repository.get_candidate(
        session, candidate_id
    ) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    pdf_bytes = file.file.read(MAX_RESUME_UPLOAD_BYTES + 1)
    if not pdf_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(pdf_bytes) > MAX_RESUME_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")
    if not pdf_bytes.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(status_code=415, detail="Uploaded file must be a PDF")

    try:
        profile = ResumeProcessor().process_resume(pdf_bytes)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if candidate_id is None:
        candidate = candidate_repository.create_candidate(
            session,
            full_name=profile.identity.full_name,
            email=profile.identity.email,
        )
        candidate_id = candidate.id

    resume = resume_repository.create_resume(session, candidate_id, profile)
    stored_profile = resume_repository.load_candidate_profile(session, resume.id)

    return ResumeUploadResponse(
        resume_id=resume.id,
        candidate_id=resume.candidate_id,
        profile=stored_profile,
    )
