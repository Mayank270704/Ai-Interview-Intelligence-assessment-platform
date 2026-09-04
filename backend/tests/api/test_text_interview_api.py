"""API tests for the end-to-end text interview flow."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.answer_intelligence.answer_analyzer import AnswerAnalyzer
from app.ai.interviewer_brain.reasoning_engine import InterviewReasoningEngine
from app.ai.llm.client import LLMClient
from app.ai.question_engine.generator import QuestionGenerator
from app.core.security import get_current_user
from app.db.base import Base
from app.db.database import get_session
from app.db.models import Candidate, Interview, InterviewTurn, Resume
from app.db.repositories import candidate_repository, interview_repository
from app.db.supabase_auth import AuthenticatedUser
from app.main import app
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill

TEST_USER = AuthenticatedUser(id="test-user-1", email="tester@example.com", access_token="test-token")
BLANK_ANSWER = "  \t \n  "


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


CLAIM_TEXT = "Improved model accuracy by 18%"


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


def _analysis(claim_text: str | None = CLAIM_TEXT) -> AnswerAnalysis:
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
        resume_claim_relationships=(
            [
                ResumeClaimRelationship(
                    claim_text=claim_text,
                    relationship="supports",
                    evidence="Candidate described the validation lift.",
                )
            ]
            if claim_text
            else []
        ),
        recommended_actions=["probe_deeper"],
        evidence=["Candidate described fine-tuning."],
    )


def _decision(
    action: str = "DEEPEN",
    target_concept: str = "tokenization",
    difficulty_direction: str = "maintain",
    resume_claim_to_investigate: str | None = None,
) -> InterviewDecision:
    return InterviewDecision(
        action=action,
        target_concept=target_concept,
        reasoning="Tokenization needs more evidence.",
        reasoning_evidence=["No tokenizer named."],
        difficulty_direction=difficulty_direction,
        resume_claim_to_investigate=resume_claim_to_investigate,
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
    return _create_resume_response(client, candidate_id).json()["resume_id"]


def _create_resume_response(client: TestClient, candidate_id: str) -> httpx.Response:
    response = client.post(
        "/api/v1/resumes",
        json={"candidate_id": candidate_id, "profile": _profile().model_dump(mode="json")},
    )
    return response


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


def test_blank_objective_is_rejected_before_the_pipeline(
    client: TestClient,
    mocked_ai,
):
    """A whitespace-only objective is not an objective, and must not reach the pipeline."""
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)

    response = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume_id, "objective": "   ", "difficulty": "medium"},
    )

    assert response.status_code == 422
    mocked_ai["generate_question"].assert_not_called()


def test_objective_is_stored_stripped(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)

    started = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume_id, "objective": "  Machine Learning  "},
    ).json()

    state = client.get(f"/api/v1/interviews/{started['interview_id']}").json()
    assert state["objective"] == "Machine Learning"


def test_blank_answer_is_rejected(client: TestClient, mocked_ai):
    """The voice and video paths reject an empty transcript; text must agree."""
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    mocked_ai["analyze_answer"].reset_mock()

    response = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": BLANK_ANSWER},
    )

    assert response.status_code == 422
    mocked_ai["analyze_answer"].assert_not_called()


def test_pipeline_failure_does_not_leak_the_provider_message(
    client: TestClient,
    mocked_ai,
):
    """An upstream model error can name quota or model internals; the caller gets the status."""
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    mocked_ai["generate_question"].side_effect = ValueError(
        "Failed to generate question: 429 RESOURCE_EXHAUSTED quota project-1234"
    )

    response = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "Answer."},
    )

    assert response.status_code == 502
    assert "RESOURCE_EXHAUSTED" not in response.text
    assert "project-1234" not in response.text


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

    assert response.status_code == 502
    turns = api_session.query(InterviewTurn).all()
    assert len(turns) == 1
    assert turns[0].id == started["turn_id"]
    assert turns[0].answer is None


def test_knowledge_state_accumulates_evidence_across_turns(
    client: TestClient,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    first = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I fine-tuned BERT."},
    ).json()
    second = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": first["next_turn_id"], "answer": "I used WordPiece."},
    ).json()

    first_concepts = {
        entry["concept"]: entry for entry in first["knowledge_state"]["concept_states"]
    }
    second_concepts = {
        entry["concept"]: entry for entry in second["knowledge_state"]["concept_states"]
    }
    assert set(second_concepts) == {"fine_tuning", "tokenization"}
    assert first_concepts["fine_tuning"]["confidence"] == "high"
    assert second_concepts["fine_tuning"]["demonstrated"] is True
    assert second["knowledge_state"]["claim_verifications"][0]["confidence"] == "high"


def test_pending_claims_are_synchronised_and_persisted(
    client: TestClient,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_response = _create_resume_response(client, candidate_id)
    resume_id = resume_response.json()["resume_id"]
    claim_id = resume_response.json()["claim_ids"][0]
    started = _start_interview(client, resume_id)
    mocked_ai["analyze_answer"].side_effect = [_analysis(None), _analysis()]

    first = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I mostly wrote glue code."},
    ).json()
    assert first["knowledge_state"]["claim_verifications"] == []

    second = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": first["next_turn_id"], "answer": "We measured an 18% lift."},
    ).json()
    assert second["knowledge_state"]["claim_verifications"][0]["claim_id"] == claim_id

    turns = client.get(f"/api/v1/interviews/{started['interview_id']}").json()["turns"]
    assert turns[0]["pending_claim_ids"] == [claim_id]
    assert turns[1]["pending_claim_ids"] == []


def test_claim_investigation_decision_carries_the_stable_claim_id(
    client: TestClient,
    mocked_ai,
):
    candidate_id = _create_candidate(client)
    resume_response = _create_resume_response(client, candidate_id)
    claim_id = resume_response.json()["claim_ids"][0]
    started = _start_interview(client, resume_response.json()["resume_id"])
    mocked_ai["analyze_answer"].return_value = _analysis(None)
    mocked_ai["decide_next_action"].return_value = _decision(
        action="INVESTIGATE_CLAIM",
        target_concept="model accuracy",
        resume_claim_to_investigate=CLAIM_TEXT,
    )

    body = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I mostly wrote glue code."},
    ).json()

    assert body["interviewer_decision"]["resume_claim_to_investigate"] == CLAIM_TEXT
    assert body["interviewer_decision"]["resume_claim_id"] == claim_id


def test_next_question_receives_the_explored_concepts(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    mocked_ai["decide_next_action"].return_value = _decision(
        action="CHANGE_TOPIC", target_concept="deployment"
    )

    client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I fine-tuned BERT."},
    )

    kwargs = mocked_ai["generate_question"].call_args.kwargs
    assert kwargs["explored_concepts"] == ["deployment"]
    assert [turn["question"] for turn in kwargs["recent_turns"]] == [
        "How did you build the sentiment model?"
    ]


def test_difficulty_progression_is_returned_and_persisted(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    assert started["difficulty"] == "medium"
    mocked_ai["decide_next_action"].return_value = _decision(
        difficulty_direction="increase"
    )

    body = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "I fine-tuned BERT."},
    ).json()

    assert body["difficulty"] == "hard"
    assert mocked_ai["generate_question"].call_args.kwargs["difficulty"] == "hard"
    state = client.get(f"/api/v1/interviews/{started['interview_id']}").json()
    assert state["difficulty"] == "hard"


def test_resume_for_unknown_candidate_returns_404(client: TestClient):
    response = _create_resume_response(client, "missing-candidate")

    assert response.status_code == 404


def test_interview_for_unknown_resume_returns_404(client: TestClient):
    response = client.post(
        "/api/v1/interviews",
        json={"resume_id": "missing-resume", "objective": "Machine Learning"},
    )

    assert response.status_code == 404


def test_interview_for_unknown_candidate_returns_404(client: TestClient):
    response = client.post(
        "/api/v1/interviews",
        json={
            "candidate_id": "missing-candidate",
            "objective": "Machine Learning",
            "candidate_profile": _profile().model_dump(mode="json"),
        },
    )

    assert response.status_code == 404


def test_interview_without_resume_or_profile_returns_400(client: TestClient):
    response = client.post(
        "/api/v1/interviews",
        json={"objective": "Machine Learning"},
    )

    assert response.status_code == 400


def test_interview_without_objective_is_rejected(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)

    response = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume_id, "objective": ""},
    )

    assert response.status_code == 422


def test_first_question_generation_failure_returns_502(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    mocked_ai["generate_question"].side_effect = ValueError(
        "Failed to generate question"
    )

    response = client.post(
        "/api/v1/interviews",
        json={"resume_id": resume_id, "objective": "Machine Learning"},
    )

    assert response.status_code == 502


def test_persistence_failure_returns_503(client: TestClient, monkeypatch):
    def fail(*args, **kwargs):
        raise SQLAlchemyError("connection lost")

    monkeypatch.setattr(candidate_repository, "create_candidate", fail)

    response = client.post("/api/v1/candidates", json={"full_name": "Jane Doe"})

    assert response.status_code == 503


def test_started_interview_is_in_progress(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)

    started = _start_interview(client, resume_id)

    assert started["status"] == "in_progress"


def test_get_interview_reflects_current_status(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    body = client.get(f"/api/v1/interviews/{started['interview_id']}").json()

    assert body["status"] == "in_progress"


def test_completing_an_interview_transitions_to_completed(
    client: TestClient, api_session: Session, mocked_ai
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)

    response = client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["interview_id"] == started["interview_id"]

    reloaded = api_session.get(Interview, started["interview_id"])
    assert reloaded.status == "completed"


def test_completed_interview_status_survives_refetch(client: TestClient, mocked_ai):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    body = client.get(f"/api/v1/interviews/{started['interview_id']}").json()

    assert body["status"] == "completed"


def test_completing_an_already_completed_interview_is_rejected(
    client: TestClient, mocked_ai
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    response = client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    assert response.status_code == 409


def test_completing_unknown_interview_returns_404(client: TestClient):
    response = client.post("/api/v1/interviews/missing/complete")

    assert response.status_code == 404


def test_completing_an_interview_still_in_created_status_is_rejected(
    client: TestClient, api_session: Session
):
    candidate = candidate_repository.create_candidate(
        api_session, full_name="Jane Doe", owner_user_id=TEST_USER.id
    )
    interview = interview_repository.create_interview(
        api_session,
        candidate_id=candidate.id,
        objective="Machine Learning",
        difficulty="medium",
    )
    api_session.commit()

    response = client.post(f"/api/v1/interviews/{interview.id}/complete")

    assert response.status_code == 409


def test_completed_interview_rejects_new_answers(
    client: TestClient, api_session: Session, mocked_ai
):
    candidate_id = _create_candidate(client)
    resume_id = _create_resume(client, candidate_id)
    started = _start_interview(client, resume_id)
    client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    response = client.post(
        f"/api/v1/interviews/{started['interview_id']}/answers",
        json={"turn_id": started["turn_id"], "answer": "Too late."},
    )

    assert response.status_code == 409
    turns = (
        api_session.query(InterviewTurn)
        .filter_by(interview_id=started["interview_id"])
        .all()
    )
    assert all(turn.answer is None for turn in turns)
