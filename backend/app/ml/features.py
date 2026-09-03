"""Turn a persisted interview turn into an ML training example.

Read-only: this never writes to the interview tables and never influences a live
interview. It runs offline, over turns whose interview is eligible (see
app.ml.consent), and drops anything it cannot represent faithfully.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ml.schema import (
    ANALYSIS_COMPLETENESS,
    ANALYSIS_CORRECTNESS,
    ANALYSIS_DEPTH,
    ANALYSIS_REASONING,
    ANALYSIS_RELEVANCE,
    EVALUATION_APPLICATION,
    EVALUATION_COMPLETENESS,
    EVALUATION_CONFIDENCE,
    EVALUATION_CORRECTNESS,
    EVALUATION_DEPTH,
    EVALUATION_REASONING,
    EVALUATION_RELEVANCE,
    EVALUATION_UNDERSTANDING,
    ExampleSource,
    TrainingExample,
    TurnFeatures,
    build_example_id,
    normalize_category,
)
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.question import GeneratedQuestion

if TYPE_CHECKING:
    from app.db.models import InterviewTurn


def extract_features(
    *,
    question: GeneratedQuestion,
    analysis: AnswerAnalysis,
    evaluation: AnswerEvaluation,
    knowledge_state: CandidateKnowledgeState | None,
    turn_number: int,
) -> TurnFeatures:
    """Reduce one turn to counts and closed-vocabulary categories.

    Free-text lists become their lengths: how many concepts the candidate
    demonstrated, never which concepts they were.
    """
    concept_states = knowledge_state.concept_states if knowledge_state else []
    claims = knowledge_state.claim_verifications if knowledge_state else []
    claim_statuses = [claim.status.strip().lower() for claim in claims]

    return TurnFeatures(
        question_difficulty=question.difficulty,
        question_intent=question.intent,
        evaluation_focus_count=len(question.evaluation_focus),
        turn_number=turn_number,
        analysis_technical_correctness=normalize_category(
            analysis.technical_correctness, ANALYSIS_CORRECTNESS
        ),
        analysis_reasoning_quality=normalize_category(
            analysis.reasoning_quality, ANALYSIS_REASONING
        ),
        analysis_answer_relevance=normalize_category(
            analysis.answer_relevance, ANALYSIS_RELEVANCE
        ),
        analysis_technical_depth=normalize_category(analysis.technical_depth, ANALYSIS_DEPTH),
        analysis_completeness=normalize_category(analysis.completeness, ANALYSIS_COMPLETENESS),
        demonstrated_concept_count=len(analysis.demonstrated_concepts),
        missing_concept_count=len(analysis.missing_concepts),
        incorrect_concept_count=len(analysis.incorrect_concepts),
        analysis_unsupported_claim_count=len(analysis.unsupported_claims),
        evaluation_technical_correctness=normalize_category(
            evaluation.technical_correctness, EVALUATION_CORRECTNESS
        ),
        evaluation_conceptual_understanding=normalize_category(
            evaluation.conceptual_understanding, EVALUATION_UNDERSTANDING
        ),
        evaluation_completeness=normalize_category(
            evaluation.completeness, EVALUATION_COMPLETENESS
        ),
        evaluation_technical_depth=normalize_category(
            evaluation.technical_depth, EVALUATION_DEPTH
        ),
        evaluation_reasoning_quality=normalize_category(
            evaluation.reasoning_quality, EVALUATION_REASONING
        ),
        evaluation_relevance=normalize_category(evaluation.relevance, EVALUATION_RELEVANCE),
        evaluation_application_ability=normalize_category(
            evaluation.application_ability, EVALUATION_APPLICATION
        ),
        evaluation_confidence=normalize_category(evaluation.confidence, EVALUATION_CONFIDENCE),
        evidence_count=len(evaluation.evidence),
        gap_count=len(evaluation.gaps),
        strength_count=len(evaluation.strengths),
        concepts_tracked=len(concept_states),
        concepts_demonstrated=sum(1 for state in concept_states if state.demonstrated),
        concepts_missing=sum(1 for state in concept_states if state.missing),
        concepts_incorrect=sum(1 for state in concept_states if state.incorrect),
        claims_supported=claim_statuses.count("supported"),
        claims_unsupported=claim_statuses.count("unsupported"),
        claims_uncertain=claim_statuses.count("uncertain"),
    )


def example_from_turn(
    turn: "InterviewTurn",
    *,
    source: ExampleSource = "consented_interview",
) -> TrainingExample | None:
    """Build a training example from one persisted turn, or None if it cannot be.

    A turn only qualifies once it carries an answer *and* everything the pipeline
    derived from it. Unanswered turns, and turns from before a pipeline change
    that left a field empty, are skipped rather than padded with defaults.
    """
    if turn.answer is None or not turn.question:
        return None
    if not turn.answer_analysis or not turn.evaluation or not turn.decision:
        return None

    question = GeneratedQuestion.model_validate(turn.question)
    analysis = AnswerAnalysis.model_validate(turn.answer_analysis)
    evaluation = AnswerEvaluation.model_validate(turn.evaluation)
    decision = InterviewDecision.model_validate(turn.decision)
    knowledge_state = (
        CandidateKnowledgeState.model_validate(turn.knowledge_state)
        if turn.knowledge_state
        else None
    )

    return TrainingExample(
        example_id=build_example_id(turn.interview_id, turn.turn_number),
        source=source,
        features=extract_features(
            question=question,
            analysis=analysis,
            evaluation=evaluation,
            knowledge_state=knowledge_state,
            turn_number=turn.turn_number,
        ),
        label_difficulty_direction=decision.difficulty_direction,
        label_action=decision.action,
        label_should_probe_further=decision.should_probe_further,
    )
