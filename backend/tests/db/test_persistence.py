"""Tests for the interview persistence slice."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Candidate, Interview, InterviewTurn, Resume, ResumeClaim
from app.db.repositories import (
    candidate_repository,
    interview_repository,
    resume_repository,
)
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill
from app.services.interview.turn_service import InterviewTurnService

ACCURACY_CLAIM = "Improved model accuracy by 18%"
TEAM_CLAIM = "Led a team of six engineers"


@pytest.fixture
def session():
    """An isolated in-memory database session for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db_session = factory()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


def _profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe", email="jane@example.com"),
        professional_summary="Machine Learning Engineer with 5 years of experience",
        skills=[Skill(name="Machine Learning")],
        claims=[
            Claim(
                claim_text=ACCURACY_CLAIM,
                category="quantitative",
                context="Sentiment analysis project",
                resume_evidence=f"{ACCURACY_CLAIM}.",
            ),
            Claim(
                claim_text=TEAM_CLAIM,
                category="domain",
                resume_evidence=f"{TEAM_CLAIM}.",
            ),
        ],
    )


def _question(text: str = "How did you build the model?", concept: str = "Machine Learning"):
    return GeneratedQuestion(
        question=text,
        target_concept=concept,
        difficulty="medium",
        intent="EXPLORE_RELATED_CONCEPT",
        evaluation_focus=["model training"],
    )


def _analysis(claim_text: str | None = None) -> AnswerAnalysis:
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
                    evidence="Reported an 18% lift on the validation set.",
                )
            ]
            if claim_text
            else []
        ),
        recommended_actions=["probe_deeper"],
        concept_evidence=[],
        evidence=["Candidate described the fine-tuning loop."],
    )


def _decision() -> InterviewDecision:
    return InterviewDecision(
        action="DEEPEN",
        target_concept="tokenization",
        reasoning="Tokenization remains under-evidenced.",
        reasoning_evidence=["No tokenizer named"],
        difficulty_direction="maintain",
        confidence="medium",
    )


def _persisted_interview(session):
    """Create a candidate, resume and interview, returning them with the stored profile."""
    candidate = candidate_repository.create_candidate(
        session, full_name="Jane Doe", email="jane@example.com"
    )
    resume = resume_repository.create_resume(session, candidate.id, _profile())
    interview = interview_repository.create_interview(
        session,
        candidate_id=candidate.id,
        objective="Machine Learning",
        difficulty="medium",
        resume_id=resume.id,
    )
    session.commit()
    profile = resume_repository.load_candidate_profile(session, resume.id)
    return candidate, resume, interview, profile


def _service(session, interview, profile) -> InterviewTurnService:
    """Build a persisting service whose LLM-backed components are mocked."""
    service = InterviewTurnService(
        interview_id=interview.id,
        interview_objective=interview.objective,
        candidate_profile=profile,
        difficulty=interview.difficulty,
        session=session,
    )
    service.question_generator.generate_question = MagicMock(return_value=_question())
    service.answer_analyzer.llm_client = MagicMock()
    service.answer_analyzer.llm_client.generate_structured.return_value = _analysis()
    service.brain.reasoning_engine.decide_next_action = MagicMock(
        return_value=_decision()
    )
    return service


def test_candidate_is_created_with_a_stable_id(session):
    """A candidate row is stored and retrievable by its generated id."""
    candidate = candidate_repository.create_candidate(
        session, full_name="Jane Doe", email="jane@example.com"
    )
    session.commit()

    loaded = candidate_repository.get_candidate(session, candidate.id)
    assert loaded is not None
    assert loaded.id == candidate.id
    assert loaded.full_name == "Jane Doe"
    assert loaded.created_at is not None


def test_resume_is_created_with_its_profile_and_claims(session):
    """The resume stores the candidate profile and one row per resume claim."""
    candidate = candidate_repository.create_candidate(session, full_name="Jane Doe")
    resume = resume_repository.create_resume(session, candidate.id, _profile())
    session.commit()

    stored = resume_repository.get_resume(session, resume.id)
    assert stored.candidate_id == candidate.id
    assert stored.profile["professional_summary"].startswith("Machine Learning Engineer")
    assert [claim.claim_text for claim in stored.claims] == [ACCURACY_CLAIM, TEAM_CLAIM]
    assert session.query(ResumeClaim).count() == 2


def test_resume_claims_receive_stable_ids_used_by_the_profile(session):
    """Claim rows and the stored profile share one stable identifier per claim."""
    candidate = candidate_repository.create_candidate(session, full_name="Jane Doe")
    resume = resume_repository.create_resume(session, candidate.id, _profile())
    session.commit()

    row_ids = [claim.id for claim in resume.claims]
    profile = resume_repository.load_candidate_profile(session, resume.id)
    profile_ids = [claim.claim_id for claim in profile.claims]

    assert profile_ids == row_ids
    assert all(claim_id for claim_id in profile_ids)
    assert len(set(profile_ids)) == 2
    assert all(claim_id not in ACCURACY_CLAIM for claim_id in profile_ids)

    reloaded = resume_repository.load_candidate_profile(session, resume.id)
    assert [claim.claim_id for claim in reloaded.claims] == profile_ids


def test_interview_is_created_for_a_candidate_and_resume(session):
    """An interview links a candidate and the resume it was started from."""
    candidate, resume, interview, _ = _persisted_interview(session)

    loaded = interview_repository.get_interview(session, interview.id)
    assert loaded.candidate_id == candidate.id
    assert loaded.resume_id == resume.id
    assert loaded.objective == "Machine Learning"
    assert loaded.difficulty == "medium"


def test_interview_turn_persists_question_answer_and_ai_output(session):
    """A turn stores the question and everything the pipeline derived from the answer."""
    _, _, interview, profile = _persisted_interview(session)
    service = _service(session, interview, profile)

    service.start_interview()
    service.submit_answer("I fine-tuned BERT on support tickets.")
    session.commit()

    turns = interview_repository.get_turns(session, interview.id)
    first = turns[0]
    assert first.turn_number == 1
    assert first.question["question"] == "How did you build the model?"
    assert first.answer == "I fine-tuned BERT on support tickets."
    assert first.answer_analysis["demonstrated_concepts"] == ["fine_tuning"]
    assert first.evaluation["technical_correctness"] == "moderate"
    assert first.decision["action"] == "DEEPEN"
    assert {
        entry["concept"] for entry in first.knowledge_state["concept_states"]
    } == {"fine_tuning", "tokenization"}


def test_multiple_turns_belong_to_one_interview(session):
    """Each asked question becomes its own numbered turn of the same interview."""
    _, _, interview, profile = _persisted_interview(session)
    service = _service(session, interview, profile)

    service.start_interview()
    service.submit_answer("First answer.")
    service.submit_answer("Second answer.")
    session.commit()

    turns = interview_repository.get_turns(session, interview.id)
    assert [turn.turn_number for turn in turns] == [1, 2, 3]
    assert {turn.interview_id for turn in turns} == {interview.id}
    assert [turn.answer for turn in turns] == ["First answer.", "Second answer.", None]


def test_claim_references_stay_stable_across_turns(session):
    """Verifications and pending claim references use the stable claim ids on every turn."""
    _, _, interview, profile = _persisted_interview(session)
    accuracy_id = profile.claims[0].claim_id
    team_id = profile.claims[1].claim_id
    service = _service(session, interview, profile)
    service.answer_analyzer.llm_client.generate_structured.side_effect = [
        _analysis(ACCURACY_CLAIM),
        _analysis(ACCURACY_CLAIM),
    ]

    service.start_interview()
    service.submit_answer("We measured an 18% lift against the baseline.")
    service.submit_answer("The baseline was the previous production model.")
    session.commit()

    turns = interview_repository.get_turns(session, interview.id)
    first_verifications = turns[0].knowledge_state["claim_verifications"]
    second_verifications = turns[1].knowledge_state["claim_verifications"]

    assert [entry["claim_id"] for entry in first_verifications] == [accuracy_id]
    assert [entry["claim_id"] for entry in second_verifications] == [accuracy_id]
    assert turns[0].pending_claim_ids == [team_id]
    assert turns[1].pending_claim_ids == [team_id]


def test_interview_can_be_reloaded_after_the_service_is_recreated(session):
    """A stored interview rebuilds into a service with its accumulated state intact."""
    _, _, interview, profile = _persisted_interview(session)
    service = _service(session, interview, profile)
    service.answer_analyzer.llm_client.generate_structured.side_effect = [
        _analysis(ACCURACY_CLAIM)
    ]

    service.start_interview()
    next_question = service.submit_answer("We measured an 18% lift against the baseline.")
    session.commit()

    restored = InterviewTurnService.load(session, interview.id)

    assert restored.interview_objective == "Machine Learning"
    assert restored.candidate_profile is not None
    assert [claim.claim_id for claim in restored.candidate_profile.claims] == [
        claim.claim_id for claim in profile.claims
    ]
    assert restored.current_question.question == next_question.question
    assert restored.brain.conversation_state.question_count == 1
    assert {
        entry.concept for entry in restored.knowledge_state.concept_states
    } == {"fine_tuning", "tokenization"}
    assert restored.knowledge_state.claim_verifications[0].claim_id == (
        profile.claims[0].claim_id
    )
    assert restored.brain.conversation_state.pending_claims == [TEAM_CLAIM]


def test_duplicate_turn_number_fails_and_the_transaction_rolls_back(session):
    """A constraint violation surfaces and leaves the interview state unchanged."""
    _, _, interview, _ = _persisted_interview(session)
    interview_repository.add_question_turn(session, interview.id, _question())
    session.commit()

    session.add(
        InterviewTurn(
            interview_id=interview.id,
            turn_number=1,
            question=_question().model_dump(mode="json"),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    assert len(interview_repository.get_turns(session, interview.id)) == 1
    assert session.query(Candidate).count() == 1
    assert session.query(Resume).count() == 1
    assert session.query(Interview).count() == 1
