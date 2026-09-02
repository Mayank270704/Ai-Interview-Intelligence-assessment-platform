"""Final interview assessment generation.

Scores are always computed deterministically (see scorer.py) from the interview's
accumulated evaluation evidence. The LLM is used only to phrase strengths, weaknesses,
and a concise summary from that same evidence -- it never invents scores, and a
deterministic fallback produces the same fields if the LLM call fails or returns
nothing usable, so the feature never depends on an LLM response to function.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.assessment.scorer import ScoredDimensions, score_interview
from app.ai.llm.client import LLMClient
from app.schemas.assessment import FinalAssessment
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.knowledge_state import CandidateKnowledgeState

_MAX_LIST_ITEMS = 5


class _AssessmentNarrative(BaseModel):
    """Structured LLM output: phrasing only, no scores and no reasoning trace."""

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    summary: str = ""


class FinalAssessmentGenerator:
    """Aggregate a completed interview's evidence into a persisted final assessment."""

    def __init__(self):
        """Initialize the generator with the configured LLM client."""
        self.llm_client = LLMClient()

    def generate(
        self,
        interview_id: str,
        objective: str,
        evaluations: list[AnswerEvaluation],
        knowledge_state: CandidateKnowledgeState | None,
    ) -> FinalAssessment:
        """Build the final assessment for one completed interview's answered turns."""
        if not evaluations:
            raise ValueError("At least one answered turn is required to score an interview.")

        dimensions = score_interview(evaluations, knowledge_state)
        strengths, weaknesses, summary = self._narrative(objective, dimensions, knowledge_state)

        return FinalAssessment(
            interview_id=interview_id,
            overall_score=dimensions.overall_score,
            technical_knowledge=dimensions.technical_knowledge,
            knowledge_depth=dimensions.knowledge_depth,
            problem_solving=dimensions.problem_solving,
            communication=dimensions.communication,
            resume_claim_accuracy=dimensions.resume_claim_accuracy,
            strengths=strengths,
            weaknesses=weaknesses,
            summary=summary,
            turns_assessed=len(evaluations),
        )

    def _narrative(
        self,
        objective: str,
        dimensions: ScoredDimensions,
        knowledge_state: CandidateKnowledgeState | None,
    ) -> tuple[list[str], list[str], str]:
        """Synthesize strengths/weaknesses/summary via the LLM, or fall back deterministically."""
        try:
            prompt = self._build_prompt(objective, dimensions, knowledge_state)
            narrative = self.llm_client.generate_structured(prompt, _AssessmentNarrative)
            if narrative.strengths and narrative.weaknesses and narrative.summary.strip():
                return (
                    list(narrative.strengths)[:_MAX_LIST_ITEMS],
                    list(narrative.weaknesses)[:_MAX_LIST_ITEMS],
                    narrative.summary.strip(),
                )
        except Exception:
            pass
        return self._deterministic_narrative(objective, dimensions, knowledge_state)

    @staticmethod
    def _build_prompt(
        objective: str,
        dimensions: ScoredDimensions,
        knowledge_state: CandidateKnowledgeState | None,
    ) -> str:
        concept_lines = [
            f"- {c.concept}: confidence={c.confidence}, demonstrated={c.demonstrated}, "
            f"missing={c.missing}, incorrect={c.incorrect}"
            for c in (knowledge_state.concept_states if knowledge_state else [])
        ]
        claim_lines = [
            f"- {c.claim_text}: status={c.status}, confidence={c.confidence}"
            for c in (knowledge_state.claim_verifications if knowledge_state else [])
        ]

        return f"""You are summarizing a completed technical interview for objective: {objective}

The numeric scores below have already been calculated from the evidence and are final.
Your only task is to phrase strengths, weaknesses, and a summary from this same evidence.

=== SCORES (already final, do not change or restate reasoning about them) ===
Overall: {dimensions.overall_score}/100
Technical knowledge: {dimensions.technical_knowledge}/100
Knowledge depth: {dimensions.knowledge_depth}/100
Problem solving: {dimensions.problem_solving}/100
Communication: {dimensions.communication}/100
Resume claim accuracy: {dimensions.resume_claim_accuracy if dimensions.resume_claim_accuracy is not None else "not assessed (no resume claims investigated)"}/100

=== CONCEPT EVIDENCE ===
{chr(10).join(concept_lines) if concept_lines else "No concept evidence recorded."}

=== RESUME CLAIM EVIDENCE ===
{chr(10).join(claim_lines) if claim_lines else "No resume claims were investigated."}

=== YOUR TASK ===
1. List 2-5 concrete strengths supported by the evidence above.
2. List 2-5 concrete weaknesses supported by the evidence above.
3. Write a concise 2-4 sentence evidence-based summary of the candidate's performance.

Do NOT:
- Invent strengths, weaknesses, or claims not supported by the evidence above.
- Describe your own reasoning process or how you reached these conclusions.
- Repeat the raw numeric scores as your summary; write about what the candidate showed.

Return valid JSON matching the required schema."""

    @staticmethod
    def _deterministic_narrative(
        objective: str,
        dimensions: ScoredDimensions,
        knowledge_state: CandidateKnowledgeState | None,
    ) -> tuple[list[str], list[str], str]:
        """Build strengths/weaknesses/summary directly from evidence, without any LLM call."""
        concept_states = knowledge_state.concept_states if knowledge_state else []

        strengths = [
            f"Demonstrated {concept.concept} with {concept.confidence} confidence."
            for concept in concept_states
            if concept.demonstrated and concept.confidence == "high"
        ][:_MAX_LIST_ITEMS]
        if not strengths:
            strengths = [
                f"Demonstrated {concept.concept}."
                for concept in concept_states
                if concept.demonstrated
            ][:_MAX_LIST_ITEMS]
        if not strengths:
            strengths = ["No clear strengths were established from the available evidence."]

        weaknesses = [
            f"{concept.concept} was not demonstrated."
            for concept in concept_states
            if concept.missing
        ][:_MAX_LIST_ITEMS]
        incorrect = [
            f"{concept.concept} showed an incorrect or misunderstood explanation."
            for concept in concept_states
            if concept.incorrect
        ]
        weaknesses = (weaknesses + incorrect)[:_MAX_LIST_ITEMS]
        if not weaknesses:
            weaknesses = ["No significant weaknesses were identified from the available evidence."]

        claim_sentence = ""
        if dimensions.resume_claim_accuracy is not None:
            claim_sentence = f" Resume claim accuracy scored {dimensions.resume_claim_accuracy}/100 based on the claims investigated."

        summary = (
            f"Across the interview on {objective}, the candidate scored {dimensions.overall_score}/100 "
            f"overall, with technical knowledge at {dimensions.technical_knowledge}/100, knowledge depth "
            f"at {dimensions.knowledge_depth}/100, problem solving at {dimensions.problem_solving}/100, "
            f"and communication at {dimensions.communication}/100.{claim_sentence}"
        )

        return strengths, weaknesses, summary
