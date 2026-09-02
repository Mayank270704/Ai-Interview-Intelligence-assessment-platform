"""Deterministic scoring of a completed interview from its accumulated evaluation evidence."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.evaluation import AnswerEvaluation
from app.schemas.knowledge_state import CandidateKnowledgeState, ClaimVerification

_TECHNICAL_CORRECTNESS_SCALE = {"strong": 100, "moderate": 65, "partial": 40, "weak": 15}
_QUALITY_SCALE = {"strong": 100, "moderate": 65, "weak": 30, "limited": 15}
_COMPLETENESS_SCALE = {"complete": 100, "partial": 60, "incomplete": 30, "vague": 15}
_DEPTH_SCALE = {"deep": 100, "moderate": 65, "shallow": 30, "limited": 15}
_RELEVANCE_SCALE = {"high": 100, "medium": 60, "low": 25, "off_topic": 0}
_CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
_CLAIM_SCALE = {
    ("supported", "high"): 100,
    ("supported", "medium"): 80,
    ("supported", "low"): 60,
    ("uncertain", "high"): 50,
    ("uncertain", "medium"): 50,
    ("uncertain", "low"): 50,
    ("unsupported", "low"): 40,
    ("unsupported", "medium"): 15,
    ("unsupported", "high"): 5,
}
_DEFAULT_SCALE_SCORE = 50
_DEFAULT_CONFIDENCE_WEIGHT = 0.5
_DEFAULT_CLAIM_SCORE = 50


@dataclass
class ScoredDimensions:
    """The deterministic, evidence-derived score for every assessed dimension."""

    overall_score: int
    technical_knowledge: int
    knowledge_depth: int
    problem_solving: int
    communication: int
    resume_claim_accuracy: int | None


def _normalize(value: str) -> str:
    return value.strip().lower()


def _scaled(value: str, scale: dict[str, int]) -> int:
    return scale.get(_normalize(value), _DEFAULT_SCALE_SCORE)


def _confidence_weight(value: str) -> float:
    return _CONFIDENCE_WEIGHT.get(_normalize(value), _DEFAULT_CONFIDENCE_WEIGHT)


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _weighted_average(scored: list[tuple[float, float]]) -> int:
    total_weight = sum(weight for _, weight in scored)
    if total_weight <= 0:
        return 0
    return _clamp(sum(score * weight for score, weight in scored) / total_weight)


def _score_claim_verifications(claims: list[ClaimVerification]) -> int | None:
    """Score resume claim accuracy from the interview's accumulated claim verifications.

    Returns None when no resume claim was ever investigated during the interview,
    since a claim-accuracy score would otherwise be invented without evidence.
    """
    if not claims:
        return None
    scores = [
        _CLAIM_SCALE.get((_normalize(claim.status), _normalize(claim.confidence)), _DEFAULT_CLAIM_SCORE)
        for claim in claims
    ]
    return _clamp(sum(scores) / len(scores))


def score_interview(
    evaluations: list[AnswerEvaluation],
    knowledge_state: CandidateKnowledgeState | None,
) -> ScoredDimensions:
    """Deterministically aggregate per-turn AnswerEvaluation evidence into dimension scores.

    Each turn contributes to technical knowledge (technical_correctness), knowledge depth
    (technical_depth), problem solving (reasoning_quality), and communication (the average
    of completeness and relevance), weighted by that turn's own evaluation confidence so
    weakly-evidenced turns influence the aggregate less than strongly-evidenced ones.
    Resume claim accuracy comes from the interview's final claim verification state, not
    from any single turn.
    """
    if not evaluations:
        raise ValueError("At least one answered turn is required to score an interview.")

    technical: list[tuple[float, float]] = []
    depth: list[tuple[float, float]] = []
    reasoning: list[tuple[float, float]] = []
    communication: list[tuple[float, float]] = []

    for evaluation in evaluations:
        weight = _confidence_weight(evaluation.confidence)
        technical.append((_scaled(evaluation.technical_correctness, _TECHNICAL_CORRECTNESS_SCALE), weight))
        depth.append((_scaled(evaluation.technical_depth, _DEPTH_SCALE), weight))
        reasoning.append((_scaled(evaluation.reasoning_quality, _QUALITY_SCALE), weight))
        communication_component = (
            _scaled(evaluation.completeness, _COMPLETENESS_SCALE)
            + _scaled(evaluation.relevance, _RELEVANCE_SCALE)
        ) / 2
        communication.append((communication_component, weight))

    technical_knowledge = _weighted_average(technical)
    knowledge_depth = _weighted_average(depth)
    problem_solving = _weighted_average(reasoning)
    communication_score = _weighted_average(communication)
    resume_claim_accuracy = _score_claim_verifications(
        knowledge_state.claim_verifications if knowledge_state else []
    )

    dimension_scores = [technical_knowledge, knowledge_depth, problem_solving, communication_score]
    if resume_claim_accuracy is not None:
        dimension_scores.append(resume_claim_accuracy)
    overall_score = _clamp(sum(dimension_scores) / len(dimension_scores))

    return ScoredDimensions(
        overall_score=overall_score,
        technical_knowledge=technical_knowledge,
        knowledge_depth=knowledge_depth,
        problem_solving=problem_solving,
        communication=communication_score,
        resume_claim_accuracy=resume_claim_accuracy,
    )
