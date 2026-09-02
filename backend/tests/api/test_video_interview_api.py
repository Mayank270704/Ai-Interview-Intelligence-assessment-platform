"""API tests for the video interview flow (transcription-based answer submission).

The Gemini-backed VoiceClient is mocked throughout, matching the same
approach used for the voice interview tests -- there are no live STT
credentials configured for this project. This milestone computes no
behavioral/emotion signals from video; see app.ai.video.provider for the
documented (unimplemented) extension point.
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
from app.ai.voice.client import VoiceClient
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
TEST_USER = AuthenticatedUser(id="test-user-1", email="tester@example.com", access_token="test-token")
OTHER_USER = AuthenticatedUser(id="test-user-2", email="other@example.com", access_token="other-token")
VALID_VIDEO = b"\x00\x00\x00\x18ftypmp42fake video bytes"


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
def mocked_ai(monkeypatch):
    monkeypatch.setattr(LLMClient, "__init__", lambda self: None)
    opening = GeneratedQuestion(
        question="How did you build the sentiment model?",
        target_concept="Machine Learning",
        difficulty="medium",
        intent="EXPLORE_RELATED_CONCEPT",
        evaluation_focus=["Machine Learning"],
    )
    follow_up = GeneratedQuestion(
        question="Which tokenizer did you use?",
        target_concept="tokenization",
        difficulty="medium",
        intent="DEEPEN",
        evaluation_focus=["tokenization"],
    )
    monkeypatch.setattr(
        QuestionGenerator, "generate_question", MagicMock(side_effect=[opening, follow_up, follow_up])
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


@pytest.fixture
def mocked_voice(monkeypatch):
    monkeypatch.setattr(VoiceClient, "__init__", lambda self: None)
    transcribe = MagicMock(return_value="I fine-tuned BERT on the dataset.")
    monkeypatch.setattr(VoiceClient, "transcribe", transcribe)
    return {"transcribe": transcribe}


def _start_interview(client: TestClient) -> dict:
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
    return started


def _video_answer(client: TestClient, interview_id: str, turn_id: str, **overrides):
    content = overrides.pop("content", VALID_VIDEO)
    content_type = overrides.pop("content_type", "video/mp4")
    return client.post(
        f"/api/v1/interviews/{interview_id}/video-answers",
        data={"turn_id": turn_id},
        files={"file": ("answer.mp4", content, content_type)},
    )


def test_video_answer_transcribes_and_returns_pipeline_outputs(
    client: TestClient, mocked_ai, mocked_voice
):
    started = _start_interview(client)

    response = _video_answer(client, started["interview_id"], started["turn_id"])

    assert response.status_code == 200
    body = response.json()
    assert body["transcribed_answer"] == "I fine-tuned BERT on the dataset."
    assert body["answered_turn"]["answer"] == "I fine-tuned BERT on the dataset."
    assert body["answer_analysis"]["demonstrated_concepts"] == ["fine_tuning"]
    assert body["next_question"]["question"] == "Which tokenizer did you use?"
    assert "signals" not in body
    mocked_voice["transcribe"].assert_called_once_with(VALID_VIDEO, "video/mp4")


def test_video_answer_requires_authentication(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = _video_answer(client, "any-id", "any-turn")
    assert response.status_code == 401


def test_video_answer_rejects_oversized_video(client: TestClient, mocked_ai, mocked_voice, monkeypatch):
    monkeypatch.setattr("app.api.v1.interviews.MAX_VIDEO_ANSWER_BYTES", 8)
    started = _start_interview(client)

    response = _video_answer(client, started["interview_id"], started["turn_id"])

    assert response.status_code == 413


def test_video_answer_rejects_unsupported_mime_type(client: TestClient, mocked_ai, mocked_voice):
    started = _start_interview(client)

    response = _video_answer(
        client, started["interview_id"], started["turn_id"], content_type="text/plain"
    )

    assert response.status_code == 415


def test_video_answer_rejects_empty_video(client: TestClient, mocked_ai, mocked_voice):
    started = _start_interview(client)

    response = _video_answer(client, started["interview_id"], started["turn_id"], content=b"")

    assert response.status_code == 422


def test_video_answer_for_unknown_interview_returns_404(client: TestClient, mocked_voice):
    response = _video_answer(client, "missing-interview", "missing-turn")
    assert response.status_code == 404


def test_video_answer_for_other_users_interview_returns_404(
    client: TestClient, mocked_ai, mocked_voice
):
    started = _start_interview(client)

    app.dependency_overrides[get_current_user] = lambda: OTHER_USER
    response = _video_answer(client, started["interview_id"], started["turn_id"])

    assert response.status_code == 404


def test_video_answer_with_wrong_turn_id_returns_404(client: TestClient, mocked_ai, mocked_voice):
    started = _start_interview(client)

    response = _video_answer(client, started["interview_id"], "missing-turn")

    assert response.status_code == 404


def test_video_answer_transcription_failure_returns_502(client: TestClient, mocked_ai, mocked_voice):
    started = _start_interview(client)
    mocked_voice["transcribe"].side_effect = RuntimeError("Gemini transcription failed: quota exceeded")

    response = _video_answer(client, started["interview_id"], started["turn_id"])

    assert response.status_code == 502


def test_video_answer_on_completed_interview_returns_409(client: TestClient, mocked_ai, mocked_voice):
    started = _start_interview(client)
    client.post(f"/api/v1/interviews/{started['interview_id']}/complete")

    response = _video_answer(client, started["interview_id"], started["turn_id"])

    assert response.status_code == 409


def test_video_answer_accepts_browser_codec_parameters(client: TestClient, mocked_ai, mocked_voice):
    """Browser MediaRecorder uploads arrive as e.g. 'video/webm;codecs=vp8,opus'."""
    started = _start_interview(client)

    response = _video_answer(
        client, started["interview_id"], started["turn_id"], content_type="video/webm;codecs=vp8,opus"
    )

    assert response.status_code == 200
    mocked_voice["transcribe"].assert_called_once_with(VALID_VIDEO, "video/webm")
