"""API tests for PDF resume upload and ingestion."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.question_engine.generator import QuestionGenerator
from app.ai.resume_intelligence.pdf_processor import PDFExtractionError
from app.ai.resume_intelligence.processor import ResumeProcessor
from app.core.security import get_current_user
from app.db import storage as resume_storage
from app.db.base import Base
from app.db.database import get_session
from app.db.models import Candidate, Resume, ResumeClaim
from app.db.repositories import resume_repository
from app.db.supabase_auth import AuthenticatedUser
from app.main import app
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill

CLAIM_TEXT = "Improved model accuracy by 18%"
VALID_PDF_HEADER = b"%PDF-1.4\n"
CORRUPT_PDF = VALID_PDF_HEADER + b"this is not a real xref table or object stream"
TEST_USER = AuthenticatedUser(id="test-user-1", email="tester@example.com", access_token="test-token")


@pytest.fixture
def api_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(api_session: Session) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        try:
            yield api_session
            api_session.commit()
        except Exception:
            api_session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe", email="jane@example.com"),
        professional_summary="Machine Learning Engineer",
        skills=[Skill(name="Machine Learning")],
        claims=[
            Claim(
                claim_text=CLAIM_TEXT,
                category="quantitative",
                context="Sentiment analysis project",
                resume_evidence=f"{CLAIM_TEXT}.",
            )
        ],
    )


@pytest.fixture
def mocked_processor(monkeypatch):
    process_resume = MagicMock(return_value=_profile())
    monkeypatch.setattr(ResumeProcessor, "process_resume", process_resume)
    monkeypatch.setattr(resume_storage, "upload_resume_pdf", MagicMock())
    return process_resume


def _upload(client: TestClient, content: bytes = VALID_PDF_HEADER + b"body", **data):
    return client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", content, "application/pdf")},
        data=data,
    )


def test_valid_pdf_upload_creates_candidate_resume_and_claims(
    client: TestClient, api_session: Session, mocked_processor
):
    response = _upload(client)

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"]
    assert body["resume_id"]
    assert body["profile"]["identity"]["full_name"] == "Jane Doe"
    assert len(body["profile"]["claims"]) == 1
    assert body["profile"]["claims"][0]["claim_id"]

    assert api_session.query(Candidate).count() == 1
    assert api_session.query(Resume).count() == 1
    claim_rows = api_session.query(ResumeClaim).all()
    assert len(claim_rows) == 1
    assert claim_rows[0].id == body["profile"]["claims"][0]["claim_id"]
    assert claim_rows[0].resume_id == body["resume_id"]
    mocked_processor.assert_called_once()


def test_upload_for_existing_candidate_reuses_it(
    client: TestClient, api_session: Session, mocked_processor
):
    candidate_response = client.post(
        "/api/v1/candidates", json={"full_name": "Existing Candidate"}
    )
    candidate_id = candidate_response.json()["id"]

    response = _upload(client, candidate_id=candidate_id)

    assert response.status_code == 200
    assert response.json()["candidate_id"] == candidate_id
    assert api_session.query(Candidate).count() == 1


def test_upload_for_unknown_candidate_returns_404(client: TestClient, mocked_processor):
    response = _upload(client, candidate_id="missing-candidate")

    assert response.status_code == 404
    mocked_processor.assert_not_called()


def test_empty_upload_is_rejected(client: TestClient, mocked_processor):
    response = _upload(client, content=b"")

    assert response.status_code == 422
    mocked_processor.assert_not_called()


def test_missing_file_is_rejected(client: TestClient):
    response = client.post("/api/v1/resumes/upload", data={})

    assert response.status_code == 422


def test_non_pdf_file_is_rejected(client: TestClient, mocked_processor):
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.txt", b"Just plain text, not a PDF.", "text/plain")},
    )

    assert response.status_code == 415
    mocked_processor.assert_not_called()


def test_oversized_upload_is_rejected(client: TestClient, monkeypatch, mocked_processor):
    monkeypatch.setattr("app.api.v1.resumes.MAX_RESUME_UPLOAD_BYTES", 16)

    response = _upload(client, content=VALID_PDF_HEADER + b"more than sixteen bytes of body")

    assert response.status_code == 413
    mocked_processor.assert_not_called()


def test_corrupt_pdf_is_rejected(client: TestClient):
    response = _upload(client, content=CORRUPT_PDF)

    assert response.status_code == 422


def test_extraction_failure_returns_422(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        ResumeProcessor,
        "process_resume",
        MagicMock(side_effect=PDFExtractionError("PDF has no pages")),
    )

    response = _upload(client)

    assert response.status_code == 422


def test_analysis_failure_returns_502(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        ResumeProcessor,
        "process_resume",
        MagicMock(side_effect=ValueError("Failed to analyze resume: quota exceeded")),
    )

    response = _upload(client)

    assert response.status_code == 502


def test_persistence_failure_returns_503(client: TestClient, monkeypatch, mocked_processor):
    monkeypatch.setattr(
        resume_repository,
        "create_resume",
        MagicMock(side_effect=SQLAlchemyError("connection lost")),
    )

    response = _upload(client)

    assert response.status_code == 503


def test_uploaded_resume_can_start_an_interview(
    client: TestClient, mocked_processor, monkeypatch
):
    opening = GeneratedQuestion(
        question="How did you build the sentiment model?",
        target_concept="Machine Learning",
        difficulty="medium",
        intent="EXPLORE_RELATED_CONCEPT",
        evaluation_focus=["Machine Learning"],
    )
    monkeypatch.setattr(
        QuestionGenerator, "generate_question", MagicMock(return_value=opening)
    )

    uploaded = _upload(client).json()
    started = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": uploaded["resume_id"],
            "objective": "Machine Learning",
            "difficulty": "medium",
        },
    )

    assert started.status_code == 200
    body = started.json()
    assert body["candidate_id"] == uploaded["candidate_id"]
    assert body["resume_id"] == uploaded["resume_id"]
    assert body["question"]["question"] == "How did you build the sentiment model?"


def test_upload_persists_the_storage_path_scoped_to_candidate_and_resume(
    client: TestClient, api_session: Session, mocked_processor
):
    response = _upload(client)

    body = response.json()
    resume = api_session.query(Resume).filter_by(id=body["resume_id"]).one()
    assert resume.storage_path == f"{body['candidate_id']}/{body['resume_id']}.pdf"


def test_upload_calls_storage_with_the_uploaded_pdf_bytes(client: TestClient, mocked_processor):
    content = VALID_PDF_HEADER + b"a specific resume body"

    _upload(client, content=content)

    resume_storage.upload_resume_pdf.assert_called_once()
    args, _ = resume_storage.upload_resume_pdf.call_args
    assert args[1] == content


def test_storage_failure_returns_502_and_persists_nothing(
    client: TestClient, api_session: Session, monkeypatch, mocked_processor
):
    monkeypatch.setattr(
        resume_storage,
        "upload_resume_pdf",
        MagicMock(side_effect=resume_storage.StorageUploadError("upload failed")),
    )

    response = _upload(client)

    assert response.status_code == 502
    assert api_session.query(Resume).count() == 0
    assert api_session.query(Candidate).count() == 0


def test_storage_failure_for_an_existing_candidate_creates_no_resume(
    client: TestClient, api_session: Session, monkeypatch, mocked_processor
):
    candidate_id = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"}).json()["id"]
    monkeypatch.setattr(
        resume_storage,
        "upload_resume_pdf",
        MagicMock(side_effect=resume_storage.StorageUploadError("upload failed")),
    )

    response = _upload(client, candidate_id=candidate_id)

    assert response.status_code == 502
    assert api_session.query(Resume).count() == 0
    assert api_session.query(Candidate).count() == 1
