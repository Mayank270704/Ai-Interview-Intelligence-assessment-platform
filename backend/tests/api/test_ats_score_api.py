"""API tests for the ATS resume score endpoint."""

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
from app.db.supabase_auth import AuthenticatedUser
from app.main import app
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Experience, Skill

CLAIM_TEXT = "Improved model accuracy by 18%"
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
        professional_summary="Machine Learning Engineer.",
        skills=[Skill(name="Python"), Skill(name="Machine Learning")],
        experience=[
            Experience(
                company="Acme",
                position="ML Engineer",
                start_date="2020",
                description="Built and deployed models using PyTorch and Kubernetes.",
            )
        ],
        claims=[
            Claim(
                claim_text=CLAIM_TEXT,
                category="quantitative",
                resume_evidence=f"{CLAIM_TEXT}.",
            )
        ],
    )


def _create_resume_via_upload(client: TestClient, monkeypatch) -> dict:
    monkeypatch.setattr(ResumeProcessor, "process_resume", MagicMock(return_value=_profile()))
    monkeypatch.setattr(resume_storage, "upload_resume_pdf", MagicMock())
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4\nbody", "application/pdf")},
    )
    return response.json()


def test_ats_score_for_existing_resume_no_job_description(client: TestClient, monkeypatch):
    uploaded = _create_resume_via_upload(client, monkeypatch)

    response = client.post(f"/api/v1/resumes/{uploaded['resume_id']}/ats-score", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == uploaded["resume_id"]
    assert body["mode"] == "readiness"
    assert 0 <= body["ats_score"] <= 100


def test_ats_score_with_job_description(client: TestClient, monkeypatch):
    uploaded = _create_resume_via_upload(client, monkeypatch)

    response = client.post(
        f"/api/v1/resumes/{uploaded['resume_id']}/ats-score",
        json={"job_description": "Looking for a Python engineer with PyTorch and Kubernetes experience."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "jd_match"
    assert "python" in body["matched_keywords"] or "python" in body["matched_skills"]


def test_ats_score_reuses_existing_extracted_profile_without_reparsing(
    client: TestClient, monkeypatch
):
    process_resume = MagicMock(return_value=_profile())
    monkeypatch.setattr(ResumeProcessor, "process_resume", process_resume)
    monkeypatch.setattr(resume_storage, "upload_resume_pdf", MagicMock())
    uploaded = _create_resume_via_upload(client, monkeypatch)
    process_resume.reset_mock()

    client.post(f"/api/v1/resumes/{uploaded['resume_id']}/ats-score", json={})

    process_resume.assert_not_called()


def test_ats_score_for_unknown_resume_returns_404(client: TestClient):
    response = client.post("/api/v1/resumes/missing-resume/ats-score", json={})

    assert response.status_code == 404


def test_ats_score_rejects_oversized_job_description(client: TestClient, monkeypatch):
    uploaded = _create_resume_via_upload(client, monkeypatch)

    response = client.post(
        f"/api/v1/resumes/{uploaded['resume_id']}/ats-score",
        json={"job_description": "x" * 20_001},
    )

    assert response.status_code == 413


def test_ats_score_response_schema_contains_all_required_fields(client: TestClient, monkeypatch):
    uploaded = _create_resume_via_upload(client, monkeypatch)

    body = client.post(
        f"/api/v1/resumes/{uploaded['resume_id']}/ats-score",
        json={"job_description": "Python engineer with Kubernetes experience."},
    ).json()

    for field in (
        "resume_id",
        "ats_score",
        "mode",
        "matched_keywords",
        "missing_keywords",
        "matched_skills",
        "missing_skills",
        "section_feedback",
        "experience_feedback",
        "project_feedback",
        "measurable_impact_feedback",
        "suggestions",
        "diagnostics",
    ):
        assert field in body, f"missing field: {field}"
    assert isinstance(body["ats_score"], int)
    assert isinstance(body["diagnostics"], list)
    for diagnostic in body["diagnostics"]:
        for diagnostic_field in ("type", "section", "affected_text", "explanation", "actionable_fix"):
            assert diagnostic_field in diagnostic
    assert "reasoning" not in body
    assert "chain_of_thought" not in body


def test_ats_diagnostics_do_not_appear_at_the_top_level_and_do_not_affect_bounds(
    client: TestClient, monkeypatch
):
    uploaded = _create_resume_via_upload(client, monkeypatch)

    body = client.post(f"/api/v1/resumes/{uploaded['resume_id']}/ats-score", json={}).json()

    assert 0 <= body["ats_score"] <= 100
    assert isinstance(body["diagnostics"], list)
    for diagnostic in body["diagnostics"]:
        assert diagnostic["type"]
        assert diagnostic["section"]
        assert diagnostic["explanation"]
        assert diagnostic["actionable_fix"]


def test_ats_scoring_does_not_call_the_llm_client(client: TestClient, monkeypatch):
    from app.ai.llm.client import LLMClient

    uploaded = _create_resume_via_upload(client, monkeypatch)

    llm_init = MagicMock(side_effect=AssertionError("LLMClient should not be constructed for ATS scoring"))
    monkeypatch.setattr(LLMClient, "__init__", llm_init)

    response = client.post(
        f"/api/v1/resumes/{uploaded['resume_id']}/ats-score",
        json={"job_description": "Python and Kubernetes engineer."},
    )

    assert response.status_code == 200
    llm_init.assert_not_called()
