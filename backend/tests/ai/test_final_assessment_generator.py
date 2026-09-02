"""Tests for final assessment generation: LLM synthesis with a deterministic fallback."""

from unittest.mock import MagicMock

import pytest

from app.ai.assessment.generator import FinalAssessmentGenerator, _AssessmentNarrative
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.knowledge_state import CandidateKnowledgeState, ConceptState


def _evaluation() -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_correctness="strong",
        conceptual_understanding="strong",
        completeness="complete",
        technical_depth="deep",
        reasoning_quality="strong",
        relevance="high",
        application_ability="strong",
        confidence="high",
        evidence=["Concrete evidence."],
    )


def _knowledge_state() -> CandidateKnowledgeState:
    return CandidateKnowledgeState(
        concept_states=[
            ConceptState(concept="fine_tuning", confidence="high", demonstrated=True, evidence=["e"]),
            ConceptState(concept="tokenization", confidence="low", missing=True, evidence=[]),
        ],
        claim_verifications=[],
        summary="",
    )


def _generator() -> FinalAssessmentGenerator:
    generator = FinalAssessmentGenerator()
    generator.llm_client = MagicMock()
    return generator


def test_generate_requires_at_least_one_evaluation():
    generator = _generator()

    with pytest.raises(ValueError, match="At least one answered turn"):
        generator.generate("interview-1", "Machine Learning", [], None)


def test_generate_uses_llm_narrative_when_it_returns_usable_content():
    generator = _generator()
    generator.llm_client.generate_structured.return_value = _AssessmentNarrative(
        strengths=["Explained fine-tuning clearly."],
        weaknesses=["Did not address tokenization."],
        summary="The candidate showed strong fine-tuning knowledge but gaps in tokenization.",
    )

    assessment = generator.generate("interview-1", "Machine Learning", [_evaluation()], _knowledge_state())

    assert assessment.strengths == ["Explained fine-tuning clearly."]
    assert assessment.weaknesses == ["Did not address tokenization."]
    assert "fine-tuning" in assessment.summary
    assert assessment.overall_score == 100
    assert assessment.turns_assessed == 1
    assert assessment.interview_id == "interview-1"


def test_generate_falls_back_deterministically_when_llm_raises():
    generator = _generator()
    generator.llm_client.generate_structured.side_effect = RuntimeError("Gemini unavailable")

    assessment = generator.generate("interview-1", "Machine Learning", [_evaluation()], _knowledge_state())

    assert assessment.strengths
    assert assessment.weaknesses
    assert "Machine Learning" in assessment.summary
    assert str(assessment.overall_score) in assessment.summary


def test_generate_falls_back_when_llm_returns_incomplete_narrative():
    generator = _generator()
    generator.llm_client.generate_structured.return_value = _AssessmentNarrative(
        strengths=[], weaknesses=[], summary=""
    )

    assessment = generator.generate("interview-1", "Machine Learning", [_evaluation()], _knowledge_state())

    assert assessment.strengths == ["Demonstrated fine_tuning with high confidence."]
    assert assessment.weaknesses == ["tokenization was not demonstrated."]


def test_deterministic_fallback_without_knowledge_state_still_produces_a_summary():
    generator = _generator()
    generator.llm_client.generate_structured.side_effect = RuntimeError("Gemini unavailable")

    assessment = generator.generate("interview-1", "Backend Engineering", [_evaluation()], None)

    assert assessment.strengths == ["No clear strengths were established from the available evidence."]
    assert assessment.weaknesses == ["No significant weaknesses were identified from the available evidence."]
    assert "Backend Engineering" in assessment.summary


def test_scores_are_never_influenced_by_the_llm_narrative_call():
    """Scores must be identical regardless of what the LLM returns for the narrative."""
    generator_a = _generator()
    generator_a.llm_client.generate_structured.return_value = _AssessmentNarrative(
        strengths=["x"], weaknesses=["y"], summary="Something entirely different."
    )
    generator_b = _generator()
    generator_b.llm_client.generate_structured.side_effect = RuntimeError("down")

    assessment_a = generator_a.generate("i1", "ML", [_evaluation()], _knowledge_state())
    assessment_b = generator_b.generate("i1", "ML", [_evaluation()], _knowledge_state())

    assert assessment_a.overall_score == assessment_b.overall_score
    assert assessment_a.technical_knowledge == assessment_b.technical_knowledge
    assert assessment_a.knowledge_depth == assessment_b.knowledge_depth
    assert assessment_a.problem_solving == assessment_b.problem_solving
    assert assessment_a.communication == assessment_b.communication
