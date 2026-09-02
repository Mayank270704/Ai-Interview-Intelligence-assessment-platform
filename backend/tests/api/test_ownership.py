"""API tests for authentication + ownership enforcement (Milestone 3).

Covers: unauthenticated rejection, invalid resource ids, cross-user rejection
(404, not 403 -- IDOR-safe), and ownership propagation across the full
candidate -> resume -> interview -> assessment chain.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.answer_intelligence.answer_analyzer import AnswerAnalyzer
from app.ai.interviewer_brain.reasoning_engine import InterviewReasoningEngine
from app.ai.llm.client import LLMClient
from app.ai.question_engine.generator import QuestionGenerator
from app.core.security import get_current_user
from app.db.base import Base
from app.db.database import get_session
from app.db.supabase_auth import AuthenticatedUser
from app.main import app
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill

CLAIM_TEXT = "Improved model accuracy by 18%"
USER_A = AuthenticatedUser(id="user-a", email="a@example.com", access_token="token-a")
USER_B = AuthenticatedUser(id="user-b", email="b@example.com", access_token="token-b")


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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _as(user: AuthenticatedUser) -> None:
    """Switch the authenticated identity used by subsequent requests on `client`."""
    app.dependency_overrides[get_current_user] = lambda: user


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
def mocked_ai(monkeypatch):
    monkeypatch.setattr(LLMClient, "__init__", lambda self: None)
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
    monkeypatch.setattr(
        AnswerAnalyzer,
        "analyze_answer",
        MagicMock(
            return_value=AnswerAnalysis(
                technical_correctness="correct",
                demonstrated_concepts=["fine_tuning"],
                missing_concepts=[],
                incorrect_concepts=[],
                reasoning_quality="strong",
                answer_relevance="high",
                technical_depth="deep",
                completeness="complete",
                unsupported_claims=[],
                resume_claim_relationships=[
                    ResumeClaimRelationship(
                        claim_text=CLAIM_TEXT, relationship="supports", evidence="Lift reported."
                    )
                ],
                recommended_actions=["probe_deeper"],
                evidence=["Candidate described fine-tuning."],
            )
        ),
    )
    monkeypatch.setattr(
        InterviewReasoningEngine,
        "decide_next_action",
        MagicMock(
            return_value=InterviewDecision(
                action="DEEPEN",
                target_concept="tokenization",
                reasoning="Needs more evidence.",
                reasoning_evidence=["No tokenizer named."],
                difficulty_direction="maintain",
                confidence="medium",
            )
        ),
    )


def _build_chain(client: TestClient) -> dict:
    """As USER_A: create a candidate, resume, and started interview."""
    _as(USER_A)
    candidate_id = client.post(
        "/api/v1/candidates", json={"full_name": "Jane Doe", "email": "jane@example.com"}
    ).json()["id"]
    resume = client.post(
        "/api/v1/resumes",
        json={"candidate_id": candidate_id, "profile": _profile().model_dump(mode="json")},
    ).json()
    started = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume["resume_id"], "objective": "Machine Learning", "difficulty": "medium"},
    ).json()
    return {"candidate_id": candidate_id, "resume_id": resume["resume_id"], **started}


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


def test_unauthenticated_candidate_creation_is_rejected(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"})
    assert response.status_code == 401


def test_unauthenticated_resume_creation_is_rejected(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post(
        "/api/v1/resumes",
        json={"candidate_id": "any-id", "profile": _profile().model_dump(mode="json")},
    )
    assert response.status_code == 401


def test_unauthenticated_interview_start_is_rejected(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post(
        "/api/v1/interviews",
        json={"resume_id": "any-id", "objective": "Machine Learning"},
    )
    assert response.status_code == 401


def test_unauthenticated_interview_read_is_rejected(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/api/v1/interviews/any-id")
    assert response.status_code == 401


def test_unauthenticated_ats_score_is_rejected(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/api/v1/resumes/any-id/ats-score", json={})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Invalid / nonexistent resource ids (authenticated)
# ---------------------------------------------------------------------------


def test_unknown_candidate_id_returns_404(client: TestClient):
    _as(USER_A)
    response = client.post(
        "/api/v1/resumes",
        json={"candidate_id": "does-not-exist", "profile": _profile().model_dump(mode="json")},
    )
    assert response.status_code == 404


def test_unknown_resume_id_returns_404(client: TestClient):
    _as(USER_A)
    response = client.post("/api/v1/resumes/does-not-exist/ats-score", json={})
    assert response.status_code == 404


def test_unknown_interview_id_returns_404(client: TestClient):
    _as(USER_A)
    response = client.get("/api/v1/interviews/does-not-exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cross-user rejection (own-resource access succeeds; another user's fails with 404)
# ---------------------------------------------------------------------------


def test_owner_can_access_their_own_candidate(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_A)
    response = client.get(f"/api/v1/interviews/{chain['interview_id']}")
    assert response.status_code == 200


def test_other_user_cannot_read_candidates_resume(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_B)
    response = client.post(
        "/api/v1/resumes",
        json={"candidate_id": chain["candidate_id"], "profile": _profile().model_dump(mode="json")},
    )
    assert response.status_code == 404


def test_other_user_cannot_score_resume(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_B)
    response = client.post(f"/api/v1/resumes/{chain['resume_id']}/ats-score", json={})
    assert response.status_code == 404


def test_other_user_cannot_start_interview_from_resume(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_B)
    response = client.post(
        "/api/v1/interviews",
        json={"resume_id": chain["resume_id"], "objective": "Machine Learning"},
    )
    assert response.status_code == 404


def test_other_user_cannot_read_interview(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_B)
    response = client.get(f"/api/v1/interviews/{chain['interview_id']}")
    assert response.status_code == 404


def test_other_user_cannot_submit_answer(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_B)
    response = client.post(
        f"/api/v1/interviews/{chain['interview_id']}/answers",
        json={"turn_id": chain["turn_id"], "answer": "Not mine to answer."},
    )
    assert response.status_code == 404


def test_other_user_cannot_complete_interview(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_B)
    response = client.post(f"/api/v1/interviews/{chain['interview_id']}/complete")
    assert response.status_code == 404


def test_other_user_cannot_read_or_create_assessment(client: TestClient, mocked_ai):
    chain = _build_chain(client)
    _as(USER_A)
    client.post(
        f"/api/v1/interviews/{chain['interview_id']}/answers",
        json={"turn_id": chain["turn_id"], "answer": "I fine-tuned BERT."},
    )
    client.post(f"/api/v1/interviews/{chain['interview_id']}/complete")

    _as(USER_B)
    assert client.get(f"/api/v1/interviews/{chain['interview_id']}/assessment").status_code == 404
    assert client.post(f"/api/v1/interviews/{chain['interview_id']}/assessment").status_code == 404


def test_other_user_starting_interview_with_own_profile_creates_separate_candidate(
    client: TestClient, api_session: Session, mocked_ai
):
    """A candidate_id is scoped per-owner: reusing someone else's id for a fresh
    profile-only start must 404 rather than silently attaching to their data."""
    chain = _build_chain(client)
    _as(USER_B)
    response = client.post(
        "/api/v1/interviews",
        json={
            "candidate_id": chain["candidate_id"],
            "objective": "Machine Learning",
            "candidate_profile": _profile().model_dump(mode="json"),
        },
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Ownership propagation across the full chain (candidate -> resume -> interview -> assessment)
# ---------------------------------------------------------------------------


def test_ownership_propagates_through_the_full_chain(
    client: TestClient, api_session: Session, mocked_ai
):
    from app.db.models import Candidate, Resume, Interview

    chain = _build_chain(client)
    _as(USER_A)
    client.post(
        f"/api/v1/interviews/{chain['interview_id']}/answers",
        json={"turn_id": chain["turn_id"], "answer": "I fine-tuned BERT."},
    )
    client.post(f"/api/v1/interviews/{chain['interview_id']}/complete")
    assessment = client.post(f"/api/v1/interviews/{chain['interview_id']}/assessment")
    assert assessment.status_code == 200

    candidate = api_session.get(Candidate, chain["candidate_id"])
    resume = api_session.get(Resume, chain["resume_id"])
    interview = api_session.get(Interview, chain["interview_id"])
    assert candidate.owner_user_id == USER_A.id
    assert resume.candidate.owner_user_id == USER_A.id
    assert interview.candidate.owner_user_id == USER_A.id

    _as(USER_A)
    assert client.get(f"/api/v1/interviews/{chain['interview_id']}/assessment").status_code == 200
