"""Feature extraction from persisted interview turns."""

from app.db.models import InterviewTurn
from app.ml.features import example_from_turn, extract_features
from app.ml.schema import UNKNOWN_CATEGORY, build_example_id
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import (
    CandidateKnowledgeState,
    ClaimVerification,
    ConceptState,
)
from app.schemas.question import GeneratedQuestion

SECRET_CONCEPT = "Acme internal payments migration"


def _question() -> GeneratedQuestion:
    return GeneratedQuestion(
        question="How did you tune the retrieval step?",
        target_concept=SECRET_CONCEPT,
        difficulty="hard",
        intent="DEEPEN",
        evaluation_focus=["retrieval", "latency"],
    )


def _analysis(**overrides) -> AnswerAnalysis:
    payload = {
        "technical_correctness": "partially_correct",
        "demonstrated_concepts": ["retrieval", "chunking"],
        "missing_concepts": ["reranking"],
        "incorrect_concepts": [],
        "reasoning_quality": "adequate",
        "answer_relevance": "high",
        "technical_depth": "moderate",
        "completeness": "partial",
        "unsupported_claims": ["Cut latency by 60%"],
        "resume_claim_relationships": [
            ResumeClaimRelationship(
                claim_text=SECRET_CONCEPT, relationship="supports", evidence="Described the rollout."
            )
        ],
        "recommended_actions": ["probe_deeper"],
        "evidence": ["Named the chunking strategy.", "Did not mention reranking."],
    }
    payload.update(overrides)
    return AnswerAnalysis(**payload)


def _evaluation(**overrides) -> AnswerEvaluation:
    payload = {
        "technical_correctness": "moderate",
        "conceptual_understanding": "moderate",
        "completeness": "partial",
        "technical_depth": "moderate",
        "reasoning_quality": "moderate",
        "relevance": "high",
        "application_ability": "moderate",
        "confidence": "medium",
        "evidence": ["Named the chunking strategy."],
        "gaps": ["No reranking discussion."],
        "strengths": ["Concrete retrieval detail."],
        "unsupported_claims": ["Cut latency by 60%"],
        "uncertainty_notes": [],
    }
    payload.update(overrides)
    return AnswerEvaluation(**payload)


def _knowledge_state() -> CandidateKnowledgeState:
    return CandidateKnowledgeState(
        concept_states=[
            ConceptState(concept="retrieval", confidence="high", demonstrated=True),
            ConceptState(concept="reranking", confidence="low", missing=True),
            ConceptState(concept="sharding", confidence="low", incorrect=True),
        ],
        claim_verifications=[
            ClaimVerification(
                claim_id="claim-1", claim_text=SECRET_CONCEPT, status="supported", confidence="high"
            ),
            ClaimVerification(
                claim_id="claim-2", claim_text="Led a team of 8", status="uncertain", confidence="low"
            ),
        ],
        summary="Solid on retrieval, thin on reranking.",
    )


def _turn(**overrides) -> InterviewTurn:
    payload = {
        "id": "turn-1",
        "interview_id": "interview-1",
        "turn_number": 4,
        "question": _question().model_dump(mode="json"),
        "answer": "I tuned the chunk size and measured recall.",
        "answer_analysis": _analysis().model_dump(mode="json"),
        "evaluation": _evaluation().model_dump(mode="json"),
        "decision": InterviewDecision(
            action="DEEPEN",
            target_concept=SECRET_CONCEPT,
            reasoning="Needs reranking detail.",
            difficulty_direction="increase",
            should_probe_further=True,
            confidence="medium",
        ).model_dump(mode="json"),
        "knowledge_state": _knowledge_state().model_dump(mode="json"),
    }
    payload.update(overrides)
    return InterviewTurn(**payload)


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------


def test_extracted_features_contain_no_interview_content():
    """Concept and claim names are resume content and must not reach the dataset."""
    example = example_from_turn(_turn())
    assert example is not None

    serialized = example.model_dump_json()
    assert SECRET_CONCEPT not in serialized
    assert "chunk size" not in serialized
    assert "retrieval" not in serialized
    assert "interview-1" not in serialized


def test_free_text_lists_become_counts():
    features = extract_features(
        question=_question(),
        analysis=_analysis(),
        evaluation=_evaluation(),
        knowledge_state=_knowledge_state(),
        turn_number=4,
    )

    assert features.demonstrated_concept_count == 2
    assert features.missing_concept_count == 1
    assert features.incorrect_concept_count == 0
    assert features.analysis_unsupported_claim_count == 1
    assert features.evidence_count == 1
    assert features.gap_count == 1
    assert features.strength_count == 1
    assert features.evaluation_focus_count == 2


def test_knowledge_state_is_summarized_as_counts():
    features = extract_features(
        question=_question(),
        analysis=_analysis(),
        evaluation=_evaluation(),
        knowledge_state=_knowledge_state(),
        turn_number=4,
    )

    assert features.concepts_tracked == 3
    assert features.concepts_demonstrated == 1
    assert features.concepts_missing == 1
    assert features.concepts_incorrect == 1
    assert features.claims_supported == 1
    assert features.claims_uncertain == 1
    assert features.claims_unsupported == 0


# ---------------------------------------------------------------------------
# Extraction behaviour
# ---------------------------------------------------------------------------


def test_labels_come_from_the_persisted_decision():
    example = example_from_turn(_turn())

    assert example is not None
    assert example.label_difficulty_direction == "increase"
    assert example.label_action == "DEEPEN"
    assert example.label_should_probe_further is True


def test_example_id_is_derived_from_the_turn():
    example = example_from_turn(_turn())

    assert example is not None
    assert example.example_id == build_example_id("interview-1", 4)


def test_unanswered_turn_produces_no_example():
    assert example_from_turn(_turn(answer=None)) is None


def test_turn_missing_derived_data_produces_no_example():
    """A partially-derived turn is skipped rather than padded with defaults."""
    assert example_from_turn(_turn(evaluation=None)) is None
    assert example_from_turn(_turn(answer_analysis=None)) is None
    assert example_from_turn(_turn(decision=None)) is None


def test_turn_without_knowledge_state_still_extracts():
    example = example_from_turn(_turn(knowledge_state=None))

    assert example is not None
    assert example.features.concepts_tracked == 0
    assert example.features.claims_supported == 0


def test_out_of_vocabulary_category_is_recorded_as_unknown():
    """The upstream fields are free strings; a novel value must not crash export."""
    turn = _turn(answer_analysis=_analysis(technical_correctness="mostly right").model_dump(mode="json"))

    example = example_from_turn(turn)

    assert example is not None
    assert example.features.analysis_technical_correctness == UNKNOWN_CATEGORY


def test_source_defaults_to_consented_interview():
    example = example_from_turn(_turn())

    assert example is not None
    assert example.source == "consented_interview"
