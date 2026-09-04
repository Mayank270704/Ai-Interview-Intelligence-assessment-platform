"""Tests for the evaluation engine."""

from app.ai.evaluation_engine.evaluator import AnswerEvaluator
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation


def test_answer_evaluation_schema_has_expected_fields():
    """Evaluation schema should expose evidence-based rubric dimensions."""
    evaluation = AnswerEvaluation(
        technical_correctness="strong",
        conceptual_understanding="moderate",
        completeness="partial",
        technical_depth="moderate",
        reasoning_quality="strong",
        relevance="high",
        application_ability="limited",
        confidence="medium",
        evidence=["Candidate explains the model architecture."],
        gaps=["Missing training details."],
        strengths=["Clear explanation of design trade-offs."],
        unsupported_claims=[],
        uncertainty_notes=["Answer does not discuss evaluation metrics."],
    )

    assert evaluation.relevance == "high"
    assert evaluation.confidence == "medium"
    assert evaluation.uncertainty_notes[0].startswith("Answer does not discuss")


def test_answer_evaluator_evaluates_answer_analysis():
    """The evaluator should derive rubric-based conclusions from answer analysis."""
    analysis = AnswerAnalysis(
        technical_correctness="partially_correct",
        demonstrated_concepts=["transformer architecture", "fine-tuning"],
        missing_concepts=["evaluation metrics"],
        incorrect_concepts=[],
        reasoning_quality="adequate",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["probe_deeper"],
        evidence=["The answer mentions the architecture and fine-tuning steps."],
    )

    evaluator = AnswerEvaluator()
    evaluation = evaluator.evaluate_answer(
        question="How did you fine-tune the model?",
        answer="I used a transformer and fine-tuned it on the labeled dataset.",
        answer_analysis=analysis,
    )

    assert isinstance(evaluation, AnswerEvaluation)
    assert evaluation.technical_correctness in {"strong", "moderate", "weak", "partial"}
    assert evaluation.conceptual_understanding in {"strong", "moderate", "weak", "limited"}
    assert "evaluation metrics" in " ".join(evaluation.gaps)
    assert evaluation.confidence in {"low", "medium", "high"}


def test_answer_evaluator_treats_missing_evidence_as_uncertain_not_disqualifying():
    """Missing evidence should not be treated as proof of insufficient knowledge."""
    analysis = AnswerAnalysis(
        technical_correctness="unknown",
        demonstrated_concepts=[],
        missing_concepts=["dataset preparation"],
        incorrect_concepts=[],
        reasoning_quality="unclear",
        answer_relevance="medium",
        technical_depth="insufficient",
        completeness="incomplete",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["clarify"],
        evidence=[],
    )

    evaluator = AnswerEvaluator()
    evaluation = evaluator.evaluate_answer(
        question="How did you prepare the dataset?",
        answer="I can discuss the dataset later.",
        answer_analysis=analysis,
    )

    assert evaluation.confidence == "low"
    assert any("missing evidence" in note.lower() for note in evaluation.uncertainty_notes)
    assert "dataset preparation" in " ".join(evaluation.gaps)
