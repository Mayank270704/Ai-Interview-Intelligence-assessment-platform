"""Tests for deterministic final-assessment scoring."""

import pytest

from app.ai.assessment.scorer import score_interview
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.knowledge_state import CandidateKnowledgeState, ClaimVerification


def _evaluation(
    technical_correctness: str = "strong",
    technical_depth: str = "deep",
    reasoning_quality: str = "strong",
    completeness: str = "complete",
    relevance: str = "high",
    confidence: str = "high",
) -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_correctness=technical_correctness,
        conceptual_understanding=reasoning_quality,
        completeness=completeness,
        technical_depth=technical_depth,
        reasoning_quality=reasoning_quality,
        relevance=relevance,
        application_ability="strong",
        confidence=confidence,
        evidence=["Concrete evidence."],
    )


def _claim(status: str, confidence: str, text: str = "Improved accuracy by 18%") -> ClaimVerification:
    return ClaimVerification(claim_id=None, claim_text=text, status=status, confidence=confidence)


def test_score_interview_requires_at_least_one_evaluation():
    with pytest.raises(ValueError, match="At least one answered turn"):
        score_interview([], None)


def test_strong_answer_scores_at_the_top_of_each_scale():
    dimensions = score_interview([_evaluation()], None)

    assert dimensions.technical_knowledge == 100
    assert dimensions.knowledge_depth == 100
    assert dimensions.problem_solving == 100
    assert dimensions.communication == 100
    assert dimensions.overall_score == 100
    assert dimensions.resume_claim_accuracy is None


def test_weak_answer_scores_at_the_bottom_of_each_scale():
    weak = _evaluation(
        technical_correctness="weak",
        technical_depth="limited",
        reasoning_quality="limited",
        completeness="vague",
        relevance="off_topic",
        confidence="high",
    )

    dimensions = score_interview([weak], None)

    assert dimensions.technical_knowledge == 15
    assert dimensions.knowledge_depth == 15
    assert dimensions.problem_solving == 15
    assert dimensions.communication == round((15 + 0) / 2)


def test_aggregation_across_two_turns_is_confidence_weighted():
    """Hand-computed: a high-confidence strong turn and a low-confidence weak turn."""
    strong = _evaluation(confidence="high")
    weak = _evaluation(
        technical_correctness="weak",
        technical_depth="limited",
        reasoning_quality="limited",
        completeness="vague",
        relevance="low",
        confidence="low",
    )

    dimensions = score_interview([strong, weak], None)

    # technical: (100*1.0 + 15*0.4) / 1.4 = 75.71.. -> 76
    assert dimensions.technical_knowledge == 76
    # depth: identical weighting/values to technical in this scenario
    assert dimensions.knowledge_depth == 76
    # reasoning: identical weighting/values
    assert dimensions.problem_solving == 76
    # communication: turn1 (100+100)/2=100 weight1.0; turn2 (15+25)/2=20 weight0.4
    # (100*1.0 + 20*0.4) / 1.4 = 77.14.. -> 77
    assert dimensions.communication == 77
    assert dimensions.overall_score == round((76 + 76 + 76 + 77) / 4)


def test_low_confidence_turns_influence_the_aggregate_less_than_high_confidence_turns():
    high_confidence_weak = _evaluation(technical_correctness="weak", confidence="high")
    low_confidence_strong = _evaluation(technical_correctness="strong", confidence="low")

    mostly_weak = score_interview([high_confidence_weak, low_confidence_strong], None)
    mostly_strong = score_interview(
        [
            _evaluation(technical_correctness="weak", confidence="low"),
            _evaluation(technical_correctness="strong", confidence="high"),
        ],
        None,
    )

    assert mostly_weak.technical_knowledge < mostly_strong.technical_knowledge


def test_unrecognized_values_fall_back_to_a_neutral_score_instead_of_crashing():
    odd = _evaluation(
        technical_correctness="somewhat_correct",
        technical_depth="unknown",
        reasoning_quality="mixed",
        completeness="unclear",
        relevance="tangential",
    )

    dimensions = score_interview([odd], None)

    assert 0 <= dimensions.technical_knowledge <= 100
    assert dimensions.technical_knowledge == 50


def test_resume_claim_accuracy_is_none_without_any_claims():
    state = CandidateKnowledgeState(concept_states=[], claim_verifications=[], summary="")

    dimensions = score_interview([_evaluation()], state)

    assert dimensions.resume_claim_accuracy is None


def test_resume_claim_accuracy_reflects_supported_and_unsupported_claims():
    state = CandidateKnowledgeState(
        concept_states=[],
        claim_verifications=[
            _claim("supported", "high"),
            _claim("unsupported", "high", text="Led a team of ten"),
        ],
        summary="",
    )

    dimensions = score_interview([_evaluation()], state)

    # (100 + 5) / 2 = 52.5 -> 52 (Python's round() rounds half to even)
    assert dimensions.resume_claim_accuracy == 52


def test_overall_score_incorporates_claim_accuracy_when_present():
    state = CandidateKnowledgeState(
        concept_states=[],
        claim_verifications=[_claim("unsupported", "high")],
        summary="",
    )

    with_claims = score_interview([_evaluation()], state)
    without_claims = score_interview([_evaluation()], None)

    assert with_claims.resume_claim_accuracy == 5
    assert with_claims.overall_score < without_claims.overall_score


@pytest.mark.parametrize(
    "technical_correctness,technical_depth,reasoning_quality,completeness,relevance,confidence",
    [
        ("strong", "deep", "strong", "complete", "high", "high"),
        ("weak", "limited", "limited", "vague", "off_topic", "low"),
        ("moderate", "moderate", "moderate", "partial", "medium", "medium"),
    ],
)
def test_all_scores_stay_within_0_to_100_bounds(
    technical_correctness, technical_depth, reasoning_quality, completeness, relevance, confidence
):
    evaluation = _evaluation(
        technical_correctness=technical_correctness,
        technical_depth=technical_depth,
        reasoning_quality=reasoning_quality,
        completeness=completeness,
        relevance=relevance,
        confidence=confidence,
    )
    state = CandidateKnowledgeState(
        concept_states=[], claim_verifications=[_claim("uncertain", "low")], summary=""
    )

    dimensions = score_interview([evaluation], state)

    for value in (
        dimensions.overall_score,
        dimensions.technical_knowledge,
        dimensions.knowledge_depth,
        dimensions.problem_solving,
        dimensions.communication,
        dimensions.resume_claim_accuracy,
    ):
        assert 0 <= value <= 100
