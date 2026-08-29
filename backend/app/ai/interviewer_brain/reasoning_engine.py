"""LLM-based reasoning for interview decisions."""

from __future__ import annotations

import json
from typing import Any

from app.ai.llm.client import LLMClient
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.resume import CandidateProfile


class InterviewReasoningEngine:
    """Use LLM reasoning to determine the next interview action based on evidence."""

    def __init__(self):
        """Initialize the reasoning engine with the configured LLM client."""
        self.llm_client = LLMClient()

    @staticmethod
    def _build_decision_prompt(
        candidate_profile: CandidateProfile | None,
        answer_analysis: AnswerAnalysis,
        answer_evaluation: AnswerEvaluation,
        knowledge_state: CandidateKnowledgeState,
        current_topic: str,
        recent_questions: list[str],
        pending_claims: list[str],
        unresolved_gaps: list[str],
        question_count: int,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build a structured prompt for reasoning about the next interview action."""
        candidate_summary = "Unknown candidate" if not candidate_profile else candidate_profile.identity.full_name or "Candidate"

        answer_analysis_json = json.dumps(
            {
                "technical_correctness": answer_analysis.technical_correctness,
                "demonstrated_concepts": answer_analysis.demonstrated_concepts,
                "missing_concepts": answer_analysis.missing_concepts,
                "incorrect_concepts": answer_analysis.incorrect_concepts,
                "reasoning_quality": answer_analysis.reasoning_quality,
                "completeness": answer_analysis.completeness,
                "technical_depth": answer_analysis.technical_depth,
                "unsupported_claims": answer_analysis.unsupported_claims,
            },
            ensure_ascii=False,
            indent=2,
        )

        knowledge_summary = json.dumps(
            {
                "concept_states": [
                    {
                        "concept": entry.concept,
                        "confidence": entry.confidence,
                        "demonstrated": entry.demonstrated,
                        "missing": entry.missing,
                        "incorrect": entry.incorrect,
                    }
                    for entry in knowledge_state.concept_states
                ],
                "summary": knowledge_state.summary,
            },
            ensure_ascii=False,
            indent=2,
        )

        prompt = f"""You are an expert technical interviewer with strong reasoning and analysis skills.

Analyze the candidate's current response and interview state to decide the next interview action.

Candidate: {candidate_summary}
Current Topic: {current_topic}
Questions Asked So Far: {question_count}

=== LATEST ANSWER ANALYSIS ===
{answer_analysis_json}

=== EVALUATION SUMMARY ===
Technical Correctness: {answer_evaluation.technical_correctness}
Conceptual Understanding: {answer_evaluation.conceptual_understanding}
Completeness: {answer_evaluation.completeness}
Technical Depth: {answer_evaluation.technical_depth}
Relevance: {answer_evaluation.relevance}
Confidence in Assessment: {answer_evaluation.confidence}
Identified Gaps: {', '.join(answer_evaluation.gaps[:3]) if answer_evaluation.gaps else 'None'}
Strengths: {', '.join(answer_evaluation.strengths[:3]) if answer_evaluation.strengths else 'None'}

=== KNOWLEDGE STATE ===
{knowledge_summary}

=== INTERVIEW CONTEXT ===
Recent Questions: {', '.join(recent_questions[-3:]) if recent_questions else 'None'}
Pending Resume Claims: {', '.join(pending_claims[:5]) if pending_claims else 'None'}
Unresolved Knowledge Gaps: {', '.join(unresolved_gaps[:5]) if unresolved_gaps else 'None'}

=== DECISION RULES ===
1. DEEPEN: The answer was strong, but deeper investigation of mechanisms or edge cases is warranted.
2. CLARIFY: The answer was vague, incomplete, or ambiguous. Probe for more detail or evidence.
3. CHALLENGE: The answer contains incorrect reasoning or unsupported claims. Challenge professionally.
4. INCREASE_DIFFICULTY: The candidate demonstrated clear mastery. Increase technical difficulty.
5. DECREASE_DIFFICULTY: The candidate is struggling or uncertain. Reduce difficulty to build foundation.
6. INVESTIGATE_CLAIM: A resume claim remains unverified and should be investigated.
7. EXPLORE_RELATED_CONCEPT: Move to a related or prerequisite concept.
8. CHANGE_TOPIC: The current topic is sufficiently explored. Move to a different area.
9. CONCLUDE_TOPIC: The topic is fully explored and verified. Close this area.

=== YOUR TASK ===
Based on ONLY the evidence provided above:
1. Choose the most appropriate next action.
2. Identify the target concept for this action.
3. Provide evidence-based reasoning explaining why this action is chosen.
4. If difficulty should change, specify the direction.
5. If changing topics, specify the next topic.
6. Assess your confidence in this decision (low/medium/high).

Do NOT:
- Invent candidate knowledge that isn't evidenced.
- Treat missing evidence as proof of lack of knowledge.
- Repeat questions about concepts already thoroughly explored.
- Ask about unrelated topics without justification.
- Assign high confidence without clear evidence.

Return valid JSON matching the InterviewDecision schema.
"""
        return prompt

    def decide_next_action(
        self,
        candidate_profile: CandidateProfile | None,
        answer_analysis: AnswerAnalysis,
        answer_evaluation: AnswerEvaluation,
        knowledge_state: CandidateKnowledgeState,
        current_topic: str,
        recent_questions: list[str] | None = None,
        pending_claims: list[str] | None = None,
        unresolved_gaps: list[str] | None = None,
        question_count: int = 0,
        context: dict[str, Any] | None = None,
    ) -> InterviewDecision:
        """Decide the next interview action based on available evidence."""
        recent_questions = recent_questions or []
        pending_claims = pending_claims or []
        unresolved_gaps = unresolved_gaps or []

        prompt = self._build_decision_prompt(
            candidate_profile=candidate_profile,
            answer_analysis=answer_analysis,
            answer_evaluation=answer_evaluation,
            knowledge_state=knowledge_state,
            current_topic=current_topic,
            recent_questions=recent_questions,
            pending_claims=pending_claims,
            unresolved_gaps=unresolved_gaps,
            question_count=question_count,
            context=context,
        )

        try:
            decision = self.llm_client.generate_structured(prompt, InterviewDecision)
            return decision
        except Exception as exc:
            raise ValueError(f"Failed to reason about next action: {exc}") from exc
