"""Deterministic serialization, dataset export, and consent eligibility."""

import json
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Candidate, Interview, InterviewTurn
from app.ml.consent import candidate_is_eligible, eligible_turns
from app.ml.dataset import (
    dataset_digest,
    deserialize_example,
    export_consented_examples,
    read_jsonl,
    serialize_example,
    write_jsonl,
)
from app.ml.synthetic import SyntheticConfig, generate_dataset
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion

SMALL = SyntheticConfig(interviews=12, seed=13)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_serialization_round_trips():
    example = generate_dataset(SMALL)[0]

    assert deserialize_example(serialize_example(example)) == example


def test_serialization_is_byte_stable_and_key_sorted():
    example = generate_dataset(SMALL)[0]
    line = serialize_example(example)

    assert line == serialize_example(example)
    payload = json.loads(line)
    assert list(payload) == sorted(payload)


def test_serialized_example_is_a_single_line():
    for example in generate_dataset(SMALL)[:5]:
        assert "\n" not in serialize_example(example)


def test_jsonl_round_trips_through_a_file(tmp_path):
    examples = generate_dataset(SMALL)
    path = tmp_path / "nested" / "dataset.jsonl"

    written = write_jsonl(examples, path)

    assert written == len(examples)
    assert list(read_jsonl(path)) == examples


def test_rewriting_the_same_dataset_produces_identical_bytes(tmp_path):
    examples = generate_dataset(SMALL)
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"

    write_jsonl(examples, first)
    write_jsonl(generate_dataset(SMALL), second)

    assert first.read_bytes() == second.read_bytes()


def test_digest_changes_when_the_data_changes():
    examples = generate_dataset(SMALL)

    assert dataset_digest(examples) == dataset_digest(list(examples))
    assert dataset_digest(examples) != dataset_digest(examples[:-1])


# ---------------------------------------------------------------------------
# Consent eligibility
# ---------------------------------------------------------------------------


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    database = factory()
    try:
        yield database
    finally:
        database.close()
        engine.dispose()


def _seed_interview(session: Session, *, candidate_id: str, consent: bool) -> str:
    session.add(
        Candidate(
            id=candidate_id,
            full_name="Jane Doe",
            email="jane@example.com",
            owner_user_id="user-a",
            ml_training_consent=consent,
        )
    )
    interview_id = f"interview-{candidate_id}"
    session.add(
        Interview(
            id=interview_id,
            candidate_id=candidate_id,
            objective="Machine Learning",
            difficulty="medium",
            status="completed",
        )
    )
    session.add(
        InterviewTurn(
            id=f"turn-{candidate_id}",
            interview_id=interview_id,
            turn_number=1,
            question=GeneratedQuestion(
                question="How did you tune retrieval?",
                target_concept="retrieval",
                difficulty="medium",
                intent="DEEPEN",
                evaluation_focus=["retrieval"],
            ).model_dump(mode="json"),
            answer="I tuned the chunk size.",
            answer_analysis=AnswerAnalysis(
                technical_correctness="correct",
                reasoning_quality="strong",
                answer_relevance="high",
                technical_depth="deep",
                completeness="complete",
            ).model_dump(mode="json"),
            evaluation=AnswerEvaluation(
                technical_correctness="strong",
                conceptual_understanding="strong",
                completeness="complete",
                technical_depth="deep",
                reasoning_quality="strong",
                relevance="high",
                application_ability="strong",
                confidence="high",
            ).model_dump(mode="json"),
            decision=InterviewDecision(
                action="DEEPEN",
                target_concept="retrieval",
                reasoning="Strong answer.",
                difficulty_direction="increase",
                confidence="high",
            ).model_dump(mode="json"),
        )
    )
    session.commit()
    return interview_id


def test_consent_defaults_to_off_for_a_new_candidate(session: Session):
    """Consent is opt-in: a candidate created without a choice is not eligible."""
    candidate = Candidate(full_name="Jane Doe", owner_user_id="user-a")
    session.add(candidate)
    session.commit()

    assert candidate.ml_training_consent is False
    assert candidate_is_eligible(candidate) is False


def test_candidate_eligibility_requires_explicit_consent():
    assert candidate_is_eligible(None) is False
    assert candidate_is_eligible(Candidate(ml_training_consent=False)) is False
    assert candidate_is_eligible(Candidate(ml_training_consent=True)) is True


def test_only_consented_turns_are_exported(session: Session):
    _seed_interview(session, candidate_id="consented", consent=True)
    _seed_interview(session, candidate_id="declined", consent=False)

    turns = eligible_turns(session)
    examples = export_consented_examples(session)

    assert [turn.interview_id for turn in turns] == ["interview-consented"]
    assert len(examples) == 1
    assert examples[0].source == "consented_interview"


def test_no_consent_means_no_training_data_at_all(session: Session):
    _seed_interview(session, candidate_id="declined", consent=False)

    assert eligible_turns(session) == []
    assert export_consented_examples(session) == []


def test_withdrawing_consent_removes_a_candidate_from_the_next_export(session: Session):
    """Eligibility is evaluated at export time, so withdrawal takes effect at once."""
    _seed_interview(session, candidate_id="consented", consent=True)
    assert len(export_consented_examples(session)) == 1

    candidate = session.get(Candidate, "consented")
    candidate.ml_training_consent = False
    session.commit()

    assert export_consented_examples(session) == []


def test_exported_examples_omit_identifying_columns(session: Session):
    _seed_interview(session, candidate_id="consented", consent=True)

    payload = serialize_example(export_consented_examples(session)[0])

    assert "jane@example.com" not in payload
    assert "Jane Doe" not in payload
    assert "interview-consented" not in payload
    assert "chunk size" not in payload
