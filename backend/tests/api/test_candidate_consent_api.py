"""Candidate consent to ML training-data use, through the API.

Consent is opt-in and defaults to off, so a candidate created by any existing
flow -- including resume upload, which creates candidates implicitly -- is not
eligible for training-data export.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.resume_intelligence.processor import ResumeProcessor
from app.core.security import get_current_user
from app.db import storage as resume_storage
from app.db.base import Base
from app.db.database import get_session
from app.db.models import Candidate
from app.db.supabase_auth import AuthenticatedUser
from app.main import app
from app.ml.consent import candidate_is_eligible
from app.schemas.resume import CandidateIdentity, CandidateProfile, Skill

TEST_USER = AuthenticatedUser(id="user-a", email="a@example.com", access_token="token-a")


@pytest.fixture
def api_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
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


def test_candidate_created_without_a_choice_does_not_consent(
    client: TestClient, api_session: Session
):
    response = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"})

    assert response.status_code == 200
    assert response.json()["ml_training_consent"] is False
    stored = api_session.get(Candidate, response.json()["id"])
    assert candidate_is_eligible(stored) is False


def test_candidate_can_explicitly_opt_in(client: TestClient, api_session: Session):
    response = client.post(
        "/api/v1/candidates",
        json={"full_name": "Jane Doe", "ml_training_consent": True},
    )

    assert response.status_code == 200
    assert response.json()["ml_training_consent"] is True
    stored = api_session.get(Candidate, response.json()["id"])
    assert candidate_is_eligible(stored) is True


def test_explicitly_declining_is_recorded(client: TestClient, api_session: Session):
    response = client.post(
        "/api/v1/candidates",
        json={"full_name": "Jane Doe", "ml_training_consent": False},
    )

    stored = api_session.get(Candidate, response.json()["id"])
    assert candidate_is_eligible(stored) is False


def test_resume_upload_does_not_silently_opt_a_candidate_in(
    client: TestClient, api_session: Session, monkeypatch
):
    """Uploading a resume creates a candidate implicitly; that must not imply consent."""
    profile = CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe", email="jane@example.com"),
        professional_summary="ML Engineer",
        skills=[Skill(name="Machine Learning")],
    )
    monkeypatch.setattr(ResumeProcessor, "__init__", lambda self: None)
    monkeypatch.setattr(ResumeProcessor, "process_resume", MagicMock(return_value=profile))
    monkeypatch.setattr(resume_storage, "upload_resume_pdf", MagicMock(return_value=None))

    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("cv.pdf", b"%PDF-1.4 fake resume bytes", "application/pdf")},
    )

    assert response.status_code == 200
    stored = api_session.get(Candidate, response.json()["candidate_id"])
    assert stored.ml_training_consent is False
    assert candidate_is_eligible(stored) is False
