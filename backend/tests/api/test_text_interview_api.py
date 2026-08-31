"""API tests for the end-to-end text interview flow."""

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
from app.db.base import Base
from app.db.database import get_session
from app.db.models import Candidate, Interview, InterviewTurn, Resume
from app.main import app
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill


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


@pytest.fixture
def mocked_ai(monkeypatch):
    monkeypatch.setattr(LLMClient, "__init__", lambda self: None)
    opening = _question("How did you build the sentiment model?", "Machine Learning")
    follow_up = _question("Which tokenizer did you use?", "tokenization", "DEEPEN")
    next_follow_up = _question("How did you validate tokenization?", "validation", "DEEPEN")
    generate_question = MagicMock(side_effect=[opening, follow_up, next_follow_up])
    analyze_answer = MagicMock(return_value=_analysis())
    decide_next_action = MagicMock(return_value=_decision())

    monkeypatch.setattr(QuestionGenerator, "generate_question", generate_question)
    monkeypatch.setattr(AnswerAnalyzer, "analyze_answer", analyze_answer)
    monkeypatch.setattr(
        InterviewReasoningEngine,
        "decide_next_action",
        decide_next_action,
    )

    return {
        "generate_question": generate_question,
        "analyze_answer": analyze_answer,
        "decide_next_action": decide_next_action,
    }


def _profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe", email="jane@example.com"),
        professional_summary="Machine Learning Engineer",
        skills=[Skill(name="Machine Learning")],
        claims=[
            Claim(
                claim_text="Improved model accuracy by 18%",
                category="quantitative",
                context="Sentiment analysis project",
                resume_evidence="Improved model accuracy by 18%.",
            )
        ],
    )


def _question(
    text: str,
    target_concept: str,
    intent: str = "EXPLORE_RELATED_CONCEPT",
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question=text,
        target_concept=target_concept,
        difficulty="medium",
        intent=intent,
        evaluation_focus=[target_concept],
    )


def _analysis() -> AnswerAnalysis:
    return AnswerAnalysis(
        technical_correctness="partially_correct",
        demonstrated_concepts=["fine_tuning"],
        missing_concepts=["tokenization"],
        incorrect_concepts=[],
        reasoning_quality="adequate",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=[],
        resume_claim_relationships=[
            ResumeClaimRelationship(
                claim_text="Improved model accuracy by 18%",
                relationship="supports",
                evidence="Candidate described the validation lift.",
            )
        ],
        recommended_actions=["probe_deeper"],
        evidence=["Candidate described fine-tuning."],
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


def _create_candidate(client: TestClient) -> str:
    response = client.post(
        "/api/v1/candidates",
        json={"full_name": "Jane Doe", "email": "jane@example.com"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_resume(client: TestClient, candidate_id: str) -> str:
    response = client.post(
        "/api/v1/resumes",
        json={"candidate_id": candidate_id, "profile": _profile().model_dump(mode="json")},
    )
    assert response.status_code == 200
    return response.json()["resume_id"]


def _start_interview(client: TestClient, resume_id: str) -> dict:
    response = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": resume_id,
            "objective": "Machine Learning",
            "difficulty": "medium",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_candidate_resume_and_interview_start_flow(
    client: TestClient,
    api_session: Session,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    assert started["candidate_id"] == candidate_id
    assert started["resume_id"] == resume_id
    assert started["question"]["question"] == "How did you build the sentiment model?"
    assert started["turn_id"]
    assert api_session.query(Candidate).count() == 1
    assert api_session.query(Resume).count() == 1
    assert api_session.query(Interview).count() == 1
    assert api_session.query(InterviewTurn).count() == 1
    mocked_ai["generate_question"].assert_called_once()


def test_submit_answer_returns_pipeline_outputs_and_persists_next_turn(
    client: TestClient,
    api_session: Session,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    response = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I fine-tuned BERT."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answered_turn"]["turn_id"] == started["turn_id"]
    assert body["answered_turn"]["answer"] == "I fine-tuned BERT."
    assert body["answer_analysis"]["demonstrated_concepts"] == ["fine_tuning"]
    assert body["evaluation"]["technical_correctness"] == "moderate"
    assert body["interviewer_decision"]["action"] == "DEEPEN"
    assert body["next_question"]["question"] == "Which tokenizer did you use?"
    assert body["next_turn_id"] != started["turn_id"]
    assert body["knowledge_state"]["summary"]

    assert mocked_ai["analyze_answer"].call_count == 1
    assert mocked_ai["decide_next_action"].call_count == 1
    assert mocked_ai["generate_question"].call_count == 2
    assert api_session.query(InterviewTurn).count() == 2


def test_multiple_answer_requests_continue_from_persistence(
    client: TestClient,
    api_session: Session,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    first = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "First answer."},
    ).json()
    second = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": first["next_turn_id"], "answer": "Second answer."},
    )

    assert second.status_code == 200
    assert api_session.query(InterviewTurn).count() == 3
    turns = (
        api_session.query(InterviewTurn)
        .filter_by(interview_id=started["interview_id"])
        .order_by(InterviewTurn.turn_number)
        .all()
    )
    assert [turn.turn_number for turn in turns] == [1, 2, 3]
    assert [turn.answer for turn in turns] == [
        "First answer.",
        "Second answer.",
        None,
    ]


def test_interview_state_returns_history(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    answer = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I fine-tuned BERT."},
    ).json()

    response = client.get(f"/api/v1/interviews/{started['interview_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["current_question"]["question"] == answer["next_question"]["question"]
    assert len(body["turns"]) == 2
    assert body["turns"][0]["answer"] == "I fine-tuned BERT."
    assert body["knowledge_state"]["concept_states"]


def test_unknown_interview_returns_404(client: TestClient):
    response = client.post(
        "/api/v1/interviews/missing/answers",
        json={"turn_id": "missing-turn", "answer": "Answer."},
    )

    assert response.status_code == 404


def test_invalid_turn_returns_404(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    response = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": "missing-turn", "answer": "Answer."},
    )

    assert response.status_code == 404


def test_turn_from_another_interview_is_rejected(client: TestClient, mocked_ai):
    first_candidate = _create_candidate(client)
    first_resume = _create_resume(client, first_candidate)
    first = _start_interview(client, first_resume)

    second_candidate = _create_candidate(client)
    second_resume = _create_resume(client, second_candidate)
    second = _start_interview(client, second_resume)

    response = client.post(
        f"/api/v1/interviews/{first['interview_id']}/answers",
        json={"turn_id": second["turn_id"], "answer": "Answer."},
    )

    assert response.status_code == 400


def test_duplicate_answer_submission_is_rejected(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    first = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "First answer."},
    )
    duplicate = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "Duplicate answer."},
    )

    assert first.status_code == 200
    assert duplicate.status_code == 409


def test_candidate_resume_relationship_is_validated(client: TestClient, mocked_ai):
    first_candidate = _create_candidate(client)
    resume_id = _create_resume(client, first_candidate)
    second_candidate = _create_candidate(client)

    response = client.post(
        "/api/v1/interviews",
        json={
            "candidate_id": second_candidate,
            "resume_id": resume_id,
            "objective": "Machine Learning",
        },
    )

    assert response.status_code == 400


def test_failed_answer_submission_does_not_corrupt_turn_state(
    client: TestClient,
    api_session: Session,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    mocked_ai["generate_question"].side_effect = ValueError("Failed to generate question")

    response = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "Answer."},
    )

    assert response.status_code == 409
    turns = api_session.query(InterviewTurn).all()
    assert len(turns) == 1
    assert turns[0].id == started["turn_id"]
    assert turns[0].answer is None
