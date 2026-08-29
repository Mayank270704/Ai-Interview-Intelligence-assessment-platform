"""Evaluation engine for converting answer analysis into evidence-based signals."""

from typing import Any

from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation


class AnswerEvaluator:
    """Convert answer intelligence output into structured, evidence-based evaluations."""

    @staticmethod
    def _map_technical_correctness(value: str) -> str:
        mapping = {
            "correct": "strong",
            "partially_correct": "moderate",
            "incorrect": "weak",
            "unknown": "partial",
        }
        return mapping.get(value, "partial")

    @staticmethod
    def _map_reasoning_quality(value: str) -> str:
        mapping = {
            "strong": "strong",
            "adequate": "moderate",
            "weak": "weak",
            "unclear": "limited",
        }
        return mapping.get(value, "limited")

    @staticmethod
    def _map_depth(value: str) -> str:
        mapping = {
            "deep": "deep",
            "moderate": "moderate",
            "shallow": "shallow",
            "insufficient": "limited",
        }
        return mapping.get(value, "limited")

    @staticmethod
    def _confidence_from_analysis(answer_analysis: AnswerAnalysis) -> str:
        evidence_count = len(answer_analysis.evidence)
        if evidence_count >= 3 and not answer_analysis.incorrect_concepts:
            return "high"
        if evidence_count >= 1 or answer_analysis.demonstrated_concepts:
            return "medium"
        return "low"

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        answer_analysis: AnswerAnalysis,
        context: dict[str, Any] | None = None,
    ) -> AnswerEvaluation:
        """Evaluate the evidence available for the current answer without inferring hidden knowledge."""
        technical_correctness = self._map_technical_correctness(
            answer_analysis.technical_correctness
        )
        conceptual_understanding = self._map_reasoning_quality(
            answer_analysis.reasoning_quality
        )
        completeness = answer_analysis.completeness
        technical_depth = self._map_depth(answer_analysis.technical_depth)
        reasoning_quality = self._map_reasoning_quality(answer_analysis.reasoning_quality)
        relevance = answer_analysis.answer_relevance
        application_ability = (
            "strong"
            if answer_analysis.demonstrated_concepts
            and answer_analysis.reasoning_quality
            in {"strong", "adequate"}
            else "limited"
        )

        evidence = list(answer_analysis.evidence) or [
            "No direct evidence was provided in the current answer."
        ]
        gaps = list(answer_analysis.missing_concepts) or [
            "No explicit gaps were identified from the available evidence."
        ]
        strengths = list(answer_analysis.demonstrated_concepts) or [
            "No explicit strengths were identified from the available evidence."
        ]
        unsupported_claims = list(answer_analysis.unsupported_claims)

        uncertainty_notes = [
            "Evaluation is based only on the evidence provided in the current answer."
        ]
        if not answer_analysis.evidence:
            uncertainty_notes.append(
                "Missing evidence is treated as uncertainty, not proof of missing knowledge."
            )
        if answer_analysis.incorrect_concepts:
            uncertainty_notes.append(
                "Some concepts appear incorrect or misunderstood and require follow-up."
            )

        return AnswerEvaluation(
            technical_correctness=technical_correctness,
            conceptual_understanding=conceptual_understanding,
            completeness=completeness,
            technical_depth=technical_depth,
            reasoning_quality=reasoning_quality,
            relevance=relevance,
            application_ability=application_ability,
            confidence=self._confidence_from_analysis(answer_analysis),
            evidence=evidence,
            gaps=gaps,
            strengths=strengths,
            unsupported_claims=unsupported_claims,
            uncertainty_notes=uncertainty_notes,
        )