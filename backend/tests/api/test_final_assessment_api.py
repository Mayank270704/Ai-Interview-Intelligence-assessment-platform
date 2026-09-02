"""API tests for the final interview assessment."""

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
from app.db.models import InterviewAssessment
from app.db.repositories import candidate_repository, interview_repository
from app.db.supabase_auth import AuthenticatedUser
from app.main import app
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill

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


def _question(text: str, target_concept: str, intent: str = "EXPLORE_RELATED_CONCEPT") -> GeneratedQuestion:
    return GeneratedQuestion(
        question=text,
        target_concept=target_concept,
        difficulty="medium",
        intent=intent,
        evaluation_focus=[target_concept],
    )


def _analysis(claim_text: str | None = CLAIM_TEXT) -> AnswerAnalysis:
    return AnswerAnalysis(
        technical_correctness="correct",
        demonstrated_concepts=["fine_tuning"],
        missing_concepts=["tokenization"],
        incorrect_concepts=[],
        reasoning_quality="strong",
        answer_relevance="high",
        technical_depth="deep",
        completeness="complete",
        unsupported_claims=[],
        resume_claim_relationships=(
            [ResumeClaimRelationship(claim_text=claim_text, relationship="supports", evidence="Lift reported.")]
            if claim_text
            else []
        ),
        recommended_actions=["probe_deeper"],
        evidence=["Candidate described fine-tuning.", "Gave a concrete metric.", "Named the dataset."],
    )


def _decision() -> InterviewDecision:
    return InterviewDecision(
        action="DEEPEN",
        target_concept="tokenization",
        reasoning="Tokenization needs more evidence.",
        reasoning_evidence=["No tokenizer named."],
        difficulty_direction="maintain",
        confidence="medium",
    )


@pytest.fixture
def mocked_ai(monkeypatch):
    monkeypatch.setattr(LLMClient, "__init__", lambda self: None)
    opening = _question("How did you build the sentiment model?", "Machine Learning")
    follow_up = _question("Which tokenizer did you use?", "tokenization", "DEEPEN")
    generate_question = MagicMock(side_effect=[opening, follow_up])
    analyze_answer = MagicMock(return_value=_analysis())
    decide_next_action = MagicMock(return_value=_decision())

    monkeypatch.setattr(QuestionGenerator, "generate_question", generate_question)
    monkeypatch.setattr(AnswerAnalyzer, "analyze_answer", analyze_answer)
    monkeypatch.setattr(InterviewReasoningEngine, "decide_next_action", decide_next_action)

    return {"generate_question": generate_question, "analyze_answer": analyze_answer}


def _completed_interview(client: TestClient) -> dict:
    """Drive a real interview through the API to a completed state with one answered turn."""
    candidate = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"}).json()
    resume = client.post(
        "/api/v1/resumes",
        json={"candidate_id": candidate["id"], "profile": _profile().model_dump(mode="json")},
    ).json()
    started = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume["resume_id"], "objective": "Machine Learning", "difficulty": "medium"},
    ).json()
    client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I fine-tuned BERT on support tickets."},
    )
    client.post(f"/api/v1/interviews/{started['interview_id']}/complete")
    return started


def test_generate_assessment_for_completed_interview_succeeds(
    client: TestClient, mocked_ai
):
    started = _completed_interview(client)

    response = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment")

    assert response.status_code == 200
    body = response.json()
    assert body["interview_id"] == started["interview_id"]
    assert body["turns_assessed"] == 1
    assert body["strengths"]
    assert body["weaknesses"]
    assert body["summary"]
    for field in (
        "overall_score",
        "technical_knowledge",
        "knowledge_depth",
        "problem_solving",
        "communication",
    ):
        assert 0 <= body[field] <= 100
    assert body["resume_claim_accuracy"] is None or 0 <= body["resume_claim_accuracy"] <= 100


def test_assessment_is_rejected_for_a_created_interview(client: TestClient, api_session: Session):
    candidate = candidate_repository.create_candidate(
        api_session, full_name="Jane Doe", owner_user_id=TEST_USER.id
    )
    interview = interview_repository.create_interview(
        api_session, candidate_id=candidate.id, objective="Machine Learning", difficulty="medium"
    )
    api_session.commit()

    response = client.post(f"/api/v1/interviews/{interview.id}/assessment")

    assert response.status_code == 409


def test_assessment_is_rejected_for_an_in_progress_interview(client: TestClient, mocked_ai):
    candidate = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"}).json()
    resume = client.post(
        "/api/v1/resumes",
        json={"candidate_id": candidate["id"], "profile": _profile().model_dump(mode="json")},
    ).json()
    started = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume["resume_id"], "objective": "Machine Learning"},
    ).json()

    response = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment")

    assert response.status_code == 409


def test_assessment_for_unknown_interview_returns_404(client: TestClient):
    response = client.post("/api/v1/interviews/missing/assessment")

    assert response.status_code == 404


def test_get_assessment_before_generation_returns_404(client: TestClient, mocked_ai):
    started = _completed_interview(client)

    response = client.get(f"/api/v1/interviews/{started['interview_id']}/assessment")

    assert response.status_code == 404


def test_get_assessment_for_unknown_interview_returns_404(client: TestClient):
    response = client.get("/api/v1/interviews/missing/assessment")

    assert response.status_code == 404


def test_assessment_persists_and_get_returns_the_same_data(
    client: TestClient, api_session: Session, mocked_ai
):
    started = _completed_interview(client)

    generated = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment").json()
    fetched = client.get(f"/api/v1/interviews/{started['interview_id']}/assessment").json()

    assert {k: v for k, v in generated.items() if k != "created_at"} == {
        k: v for k, v in fetched.items() if k != "created_at"
    }
    assert api_session.query(InterviewAssessment).count() == 1


def test_repeated_generate_calls_do_not_create_duplicate_assessments(
    client: TestClient, api_session: Session, mocked_ai
):
    started = _completed_interview(client)

    first = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment").json()
    second = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment").json()

    assert {k: v for k, v in first.items() if k != "created_at"} == {
        k: v for k, v in second.items() if k != "created_at"
    }
    assert api_session.query(InterviewAssessment).count() == 1


def test_assessment_rejected_when_interview_has_no_answered_turns(
    client: TestClient, mocked_ai
):
    candidate = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"}).json()
    resume = client.post(
        "/api/v1/resumes",
        json={"candidate_id": candidate["id"], "profile": _profile().model_dump(mode="json")},
    ).json()
    started = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume["resume_id"], "objective": "Machine Learning"},
    ).json()
    client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    response = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment")

    assert response.status_code == 422


def test_assessment_does_not_expose_internal_reasoning_fields(client: TestClient, mocked_ai):
    started = _completed_interview(client)

    body = client.post(f"/api/v1/interviews/{started['interview_id']}/assessment").json()

    assert "reasoning" not in body
    assert "reasoning_evidence" not in body
    assert "chain_of_thought" not in body
