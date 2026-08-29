"""Tests for answer intelligence analysis."""

from unittest.mock import MagicMock

import pytest

from app.ai.answer_intelligence.answer_analyzer import AnswerAnalyzer
from app.schemas.answer import AnswerAnalysis
from app.schemas.resume import CandidateProfile, CandidateIdentity


def test_answer_analysis_schema_has_expected_fields():
    """Answer analysis schema should capture relevant assessment dimensions."""
    analysis = AnswerAnalysis(
        technical_correctness="partially_correct",
        demonstrated_concepts=["BERT fine-tuning"],
        missing_concepts=["tokenization"],
        incorrect_concepts=[],
        reasoning_quality="adequate",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["probe_deeper"],
        evidence=["Candidate described fine-tuning steps."],
    )

    assert analysis.technical_correctness == "partially_correct"
    assert "BERT fine-tuning" in analysis.demonstrated_concepts
    assert analysis.recommended_actions == ["probe_deeper"]


def test_answer_analyzer_builds_profile_summary():
    """The analyzer should summarize a candidate profile without inventing facts."""
    profile = CandidateProfile(
        identity=CandidateIdentity(
            full_name="Jane Doe",
            email="jane@example.com",
            location="Seattle, WA",
        ),
        professional_summary="Machine Learning Engineer",
        skills=[],
        technologies=[],
        experience=[],
        projects=[],
        certifications=[],
        achievements=[],
        claims=[],
    )

    analyzer = AnswerAnalyzer()
    summary = analyzer._build_candidate_summary(profile)

    assert "Jane Doe" in summary
    assert "Machine Learning Engineer" in summary
    assert "Seattle, WA" in summary


def test_answer_analyzer_uses_llm_for_structured_analysis():
    """The analyzer should delegate to the LLM abstraction for structured output."""
    analyzer = AnswerAnalyzer()
    analyzer.llm_client = MagicMock()

    result = AnswerAnalysis(
        technical_correctness="correct",
        demonstrated_concepts=["transformers"],
        missing_concepts=[],
        incorrect_concepts=[],
        reasoning_quality="strong",
        answer_relevance="high",
        technical_depth="deep",
        completeness="complete",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["increase_difficulty"],
        evidence=["Correct explanation of fine-tuning."],
    )
    analyzer.llm_client.generate_structured.return_value = result

    analysis = analyzer.analyze_answer(
        question="How did you fine-tune BERT?",
        answer="I fine-tuned BERT with a custom head and validated on a held-out set.",
        candidate_profile=None,
        interview_context={"topic": "NLP"},
    )

    assert analysis.technical_correctness == "correct"
    analyzer.llm_client.generate_structured.assert_called_once()


def test_answer_analyzer_handles_llm_errors():
    """The analyzer should raise a clear error if LLM structured analysis fails."""
    analyzer = AnswerAnalyzer()
    analyzer.llm_client = MagicMock()
    analyzer.llm_client.generate_structured.side_effect = RuntimeError("API failure")

    with pytest.raises(ValueError, match="Failed to analyze answer"):
        analyzer.analyze_answer(
            question="Explain your approach.",
            answer="I used a standard pipeline.",
            candidate_profile=None,
            interview_context=None,
        )
