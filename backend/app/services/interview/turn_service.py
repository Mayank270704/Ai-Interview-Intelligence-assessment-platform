"""Interview turn orchestration across the existing interview intelligence components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.answer_intelligence.answer_analyzer import AnswerAnalyzer
from app.ai.evaluation_engine.evaluator import AnswerEvaluator
from app.ai.interviewer_brain.orchestrator import InterviewerBrainOrchestrator
from app.ai.knowledge_intelligence.knowledge_state import KnowledgeStateTracker
from app.ai.question_engine.generator import QuestionGenerator
from app.db.models import InterviewTurn
from app.db.repositories import interview_repository, resume_repository
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import DifficultyDirection, InterviewDecision
from app.schemas.knowledge import RetrievedKnowledge
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.question import GeneratedQuestion, QuestionDifficulty
from app.schemas.resume import CandidateProfile

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

DIFFICULTY_LEVELS: tuple[QuestionDifficulty, ...] = ("easy", "medium", "hard")


class InterviewTurnService:
    """Run one interview turn by coordinating the existing intelligence components.

    The service owns no interview reasoning of its own: the Interviewer Brain decides the
    action, the Question Engine phrases the question, Answer Intelligence analyzes the
    answer, the Evaluation Engine assesses the evidence, and the Knowledge State tracker
    records what the evidence implies. It is transport-independent, and when a database
    session is supplied it persists each turn through the interview repository so the
    interview can be reconstructed later.
    """

    def __init__(
        self,
        interview_id: str,
        interview_objective: str,
        candidate_profile: CandidateProfile | None = None,
        difficulty: QuestionDifficulty = "medium",
        session: "Session | None" = None,
    ):
        """Initialize an interview turn pipeline for one interview."""
        if not interview_objective.strip():
            raise ValueError("An interview objective is required to start an interview.")

        self.interview_id = interview_id
        self.interview_objective = interview_objective.strip()
        self.candidate_profile = candidate_profile
        self.difficulty: QuestionDifficulty = difficulty
        self.session = session

        self.brain = InterviewerBrainOrchestrator(interview_id)
        self.question_generator = QuestionGenerator()
        self.answer_analyzer = AnswerAnalyzer()
        self.evaluator = AnswerEvaluator()
        self.knowledge_tracker = KnowledgeStateTracker()

        self.knowledge_state = CandidateKnowledgeState()
        self.current_question: GeneratedQuestion | None = None
        self._current_turn: InterviewTurn | None = None

        self._sync_pending_claims()

    def start_interview(
        self, retrieved_knowledge: list[RetrievedKnowledge] | None = None
    ) -> GeneratedQuestion:
        """Generate the opening question from the candidate context and interview objective."""
        if self.current_question is not None:
            raise ValueError(
                f"Interview {self.interview_id} has already produced a question."
            )

        opening_decision = InterviewDecision(
            action="EXPLORE_RELATED_CONCEPT",
            target_concept=self.interview_objective,
            reasoning=(
                "Opening turn: no candidate answers have been collected yet, so the "
                "interview starts on the stated interview objective."
            ),
            reasoning_evidence=[],
            difficulty_direction="maintain",
            next_topic=self.interview_objective,
            confidence="low",
        )

        question = self.question_generator.generate_question(
            decision=opening_decision,
            difficulty=self.difficulty,
            candidate_profile=self.candidate_profile,
            retrieved_knowledge=retrieved_knowledge,
        )

        self.brain.conversation_state.current_topic = question.target_concept
        self.current_question = question
        self._persist_question(question)
        return question

    def submit_answer(
        self,
        answer: str,
        retrieved_knowledge: list[RetrievedKnowledge] | None = None,
    ) -> GeneratedQuestion:
        """Run a full interview turn on the candidate's answer and return the next question."""
        if self.current_question is None:
            raise ValueError(
                f"Interview {self.interview_id} has no pending question to answer."
            )

        asked_question = self.current_question

        analysis = self.answer_analyzer.analyze_answer(
            question=asked_question.question,
            answer=answer,
            candidate_profile=self.candidate_profile,
            interview_context=self.brain.get_interview_state(),
        )
        evaluation = self.evaluator.evaluate_answer(
            question=asked_question.question,
            answer=answer,
            answer_analysis=analysis,
        )
        self.knowledge_state = self.knowledge_tracker.update_from_answer(
            question=asked_question.question,
            answer=answer,
            answer_analysis=analysis,
            answer_evaluation=evaluation,
            current_state=self.knowledge_state,
            resume_claims=(
                self.candidate_profile.claims if self.candidate_profile else None
            ),
        )

        self._sync_pending_claims()

        decision = self.brain.decide_next_action(
            candidate_profile=self.candidate_profile,
            question=asked_question.question,
            candidate_answer=answer,
            answer_analysis=analysis,
            answer_evaluation=evaluation,
            knowledge_state=self.knowledge_state,
            current_topic=asked_question.target_concept,
        )

        self.difficulty = self._select_difficulty(decision.difficulty_direction)

        question = self.question_generator.generate_question(
            decision=decision,
            difficulty=self.difficulty,
            candidate_profile=self.candidate_profile,
            answer_evaluation=evaluation,
            knowledge_state=self.knowledge_state,
            recent_turns=self.brain.conversation_state.get_recent_turns(3),
            explored_concepts=list(self.brain.conversation_state.explored_concepts),
            retrieved_knowledge=retrieved_knowledge,
        )

        self._persist_answer(answer, analysis, evaluation, decision)

        self.current_question = question
        self._persist_question(question)
        return question

    @classmethod
    def load(
        cls,
        session: "Session",
        interview_id: str,
    ) -> "InterviewTurnService":
        """Rebuild the service for a stored interview, including its accumulated state."""
        interview = interview_repository.get_interview(session, interview_id)
        if interview is None:
            raise ValueError(f"Interview {interview_id} was not found.")

        profile = (
            resume_repository.load_candidate_profile(session, interview.resume_id)
            if interview.resume_id
            else None
        )
        service = cls(
            interview_id=interview.id,
            interview_objective=interview.objective,
            candidate_profile=profile,
            difficulty=interview.difficulty,
            session=session,
        )

        pending_claim_ids: list[str] | None = None
        for turn in interview_repository.get_turns(session, interview_id):
            question = GeneratedQuestion.model_validate(turn.question)
            service.difficulty = question.difficulty

            if turn.answer is None:
                service.current_question = question
                service._current_turn = turn
                continue

            decision = (
                InterviewDecision.model_validate(turn.decision) if turn.decision else None
            )
            target_concept = decision.target_concept if decision else question.target_concept
            service.brain.conversation_state.add_turn(
                question=question.question,
                answer=turn.answer,
                action=decision.action if decision else None,
                target_concept=target_concept,
            )
            service.brain.conversation_state.current_topic = target_concept
            if decision and decision.action in {"CONCLUDE_TOPIC", "CHANGE_TOPIC"}:
                service.brain.conversation_state.mark_concept_explored(target_concept)
            if turn.knowledge_state:
                service.knowledge_state = CandidateKnowledgeState.model_validate(
                    turn.knowledge_state
                )
            pending_claim_ids = turn.pending_claim_ids

        service._restore_pending_claims(pending_claim_ids)
        return service

    def _persist_question(self, question: GeneratedQuestion) -> None:
        """Record a newly asked question as the interview's next turn."""
        if self.session is None:
            return
        self._current_turn = interview_repository.add_question_turn(
            self.session, self.interview_id, question
        )

    def _persist_answer(
        self,
        answer: str,
        analysis: AnswerAnalysis,
        evaluation: AnswerEvaluation,
        decision: InterviewDecision,
    ) -> None:
        """Record the answer and everything derived from it against the asked turn."""
        if self.session is None or self._current_turn is None:
            return
        interview_repository.record_answer(
            self.session,
            turn=self._current_turn,
            answer=answer,
            answer_analysis=analysis,
            evaluation=evaluation,
            decision=decision,
            knowledge_state=self.knowledge_state,
            pending_claim_ids=self._pending_claim_ids(),
        )

    def _pending_claim_ids(self) -> list[str]:
        """Stable identifiers of the resume claims still pending investigation."""
        if self.candidate_profile is None:
            return []
        ids_by_text = {
            claim.claim_text: claim.claim_id
            for claim in self.candidate_profile.claims
            if claim.claim_id
        }
        return [
            ids_by_text[text]
            for text in self.brain.conversation_state.pending_claims
            if text in ids_by_text
        ]

    def _restore_pending_claims(self, pending_claim_ids: list[str] | None) -> None:
        """Restore the pending claim list recorded on the last answered turn."""
        if pending_claim_ids is None or self.candidate_profile is None:
            return
        pending = set(pending_claim_ids)
        for claim in self.candidate_profile.claims:
            if claim.claim_id and claim.claim_id not in pending:
                self.brain.mark_claim_investigated(claim.claim_text)

    def _sync_pending_claims(self) -> None:
        """Keep the brain's pending claims aligned with the accumulated verification state."""
        if self.candidate_profile is None:
            return

        verified = set(
            self.knowledge_tracker.sufficiently_verified_claims(self.knowledge_state)
        )
        for claim in self.candidate_profile.claims:
            if claim.claim_text in verified:
                self.brain.mark_claim_investigated(claim.claim_text)
            else:
                self.brain.conversation_state.add_pending_claim(claim.claim_text)

    def _select_difficulty(self, direction: DifficultyDirection) -> QuestionDifficulty:
        """Apply the decided difficulty direction to the current difficulty level."""
        index = DIFFICULTY_LEVELS.index(self.difficulty)
        if direction == "increase":
            index = min(index + 1, len(DIFFICULTY_LEVELS) - 1)
        elif direction == "decrease":
            index = max(index - 1, 0)
        return DIFFICULTY_LEVELS[index]
