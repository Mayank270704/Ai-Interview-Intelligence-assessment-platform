"""Interview orchestration and decision-making."""

from __future__ import annotations

from typing import Any

from app.ai.interviewer_brain.conversation_state import InterviewConversationState
from app.ai.interviewer_brain.reasoning_engine import InterviewReasoningEngine
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.resume import CandidateProfile


class InterviewerBrainOrchestrator:
    """Main orchestrator for interview decision-making and candidate assessment."""

    def __init__(self, interview_id: str):
        """Initialize the interviewer brain for a specific interview."""
        self.interview_id = interview_id
        self.conversation_state = InterviewConversationState(interview_id)
        self.reasoning_engine = InterviewReasoningEngine()

    def decide_next_action(
        self,
        candidate_profile: CandidateProfile | None,
        question: str,
        candidate_answer: str,
        answer_analysis: AnswerAnalysis,
        answer_evaluation: AnswerEvaluation,
        knowledge_state: CandidateKnowledgeState,
        current_topic: str = "Technical Foundation",
        context: dict[str, Any] | None = None,
    ) -> InterviewDecision:
        """
        Determine the next interview action based on candidate response and current state.

        This is the core decision-making method that orchestrates all available
        intelligence systems to produce an interview action without generating the
        final question text.
        """
        recent_questions = [
            turn["question"] for turn in self.conversation_state.get_recent_turns(5)
        ]

        decision = self.reasoning_engine.decide_next_action(
            candidate_profile=candidate_profile,
            answer_analysis=answer_analysis,
            answer_evaluation=answer_evaluation,
            knowledge_state=knowledge_state,
            current_topic=current_topic,
            recent_questions=recent_questions,
            pending_claims=self.conversation_state.pending_claims,
            unresolved_gaps=self.conversation_state.unresolved_gaps,
            question_count=self.conversation_state.question_count,
            context=context,
        )
        decision = self._attach_claim_identity(decision)

        self._record_turn_and_update_state(
            question=question,
            answer=candidate_answer,
            action=decision.action,
            target_concept=decision.target_concept,
        )

        return decision

    def _attach_claim_identity(self, decision: InterviewDecision) -> InterviewDecision:
        """Resolve the decision's free-text claim reference to the stable claim id."""
        claim_text = decision.resume_claim_to_investigate
        claim_id = (
            self.conversation_state.pending_claim_id_for_text(claim_text)
            if claim_text
            else None
        )
        if claim_id == decision.resume_claim_id:
            return decision
        return decision.model_copy(update={"resume_claim_id": claim_id})

    def _record_turn_and_update_state(
        self,
        question: str,
        answer: str,
        action: str,
        target_concept: str,
    ) -> None:
        """Record the Q&A turn and update internal state based on the interview action."""
        self.conversation_state.add_turn(
            question=question,
            answer=answer,
            action=action,
            target_concept=target_concept,
        )
        self.conversation_state.current_topic = target_concept

        if action in {"CONCLUDE_TOPIC", "CHANGE_TOPIC"}:
            self.conversation_state.mark_concept_explored(target_concept)

    def mark_claim_investigated(self, claim_id: str) -> None:
        """Mark the resume claim with this stable id as having been investigated."""
        self.conversation_state.resolve_pending_claim(claim_id)

    def mark_gap_resolved(self, gap: str) -> None:
        """Mark a knowledge gap as resolved."""
        self.conversation_state.resolve_gap(gap)

    def get_interview_state(self) -> dict[str, Any]:
        """Get the current interview state for reporting or persistence."""
        return self.conversation_state.get_state_summary()
