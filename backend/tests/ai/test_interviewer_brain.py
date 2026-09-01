"""Tests for the Interviewer Brain V1."""

from unittest.mock import patch

from app.ai.interviewer_brain.conversation_state import InterviewConversationState
from app.ai.interviewer_brain.orchestrator import InterviewerBrainOrchestrator
from app.ai.interviewer_brain.reasoning_engine import InterviewReasoningEngine
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge_state import CandidateKnowledgeState, ConceptState
from app.schemas.resume import CandidateProfile, CandidateIdentity


def test_conversation_state_tracks_interview_turns():
    """Conversation state should track Q&A turns and interview context."""
    state = InterviewConversationState("interview_123")
    assert state.question_count == 0

    state.add_turn(
        question="Explain transformers.",
        answer="Transformers use attention mechanisms.",
        action="DEEPEN",
        target_concept="attention_mechanisms",
    )

    assert state.question_count == 1
    assert len(state.conversation_turns) == 1
    assert state.conversation_turns[0]["question"] == "Explain transformers."
    assert state.conversation_turns[0]["action"] == "DEEPEN"


def test_conversation_state_tracks_explored_concepts():
    """Conversation state should track which concepts have been explored."""
    state = InterviewConversationState("interview_123")

    assert not state.has_explored_concept("transformers")
    state.mark_concept_explored("transformers")
    assert state.has_explored_concept("transformers")
    assert state.has_explored_concept("Transformers")


def test_conversation_state_tracks_pending_claims_and_gaps():
    """Conversation state should track pending resume claims by their stable id."""
    state = InterviewConversationState("interview_123")

    state.add_pending_claim("claim-accuracy", "Improved model accuracy by 18%")
    state.add_unresolved_gap("No details about evaluation metrics")

    assert state.pending_claim_ids == ["claim-accuracy"]
    assert state.pending_claims == ["Improved model accuracy by 18%"]
    assert "No details about evaluation metrics" in state.unresolved_gaps

    state.resolve_pending_claim("claim-accuracy")
    assert state.pending_claim_ids == []
    assert state.pending_claims == []


def test_reasoning_engine_decides_deepen_for_strong_answer():
    """When answer is strong but incomplete, reasoning should suggest DEEPEN."""
    analysis = AnswerAnalysis(
        technical_correctness="correct",
        demonstrated_concepts=["transformer architecture", "attention mechanism"],
        missing_concepts=["edge_cases"],
        incorrect_concepts=[],
        reasoning_quality="strong",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["probe_deeper"],
        evidence=["Candidate explained encoder-decoder structure clearly."],
    )
    evaluation = AnswerEvaluation(
        technical_correctness="strong",
        conceptual_understanding="strong",
        completeness="partial",
        technical_depth="moderate",
        reasoning_quality="strong",
        relevance="high",
        application_ability="strong",
        confidence="high",
        evidence=["Clear architecture explanation."],
        gaps=["edge cases"],
        strengths=["transformer architecture"],
        unsupported_claims=[],
        uncertainty_notes=[],
    )
    knowledge_state = CandidateKnowledgeState(
        concept_states=[
            ConceptState(
                concept="transformer_architecture",
                confidence="high",
                demonstrated=True,
                missing=False,
                incorrect=False,
                evidence=["Explained encoder-decoder structure."],
            )
        ],
        summary="Strong evidence for transformer architecture.",
    )

    engine = InterviewReasoningEngine()
    with patch.object(engine.llm_client, "generate_structured") as mock_gen:
        mock_decision = InterviewDecision(
            action="DEEPEN",
            target_concept="transformer_architecture",
            reasoning="Answer demonstrates solid understanding; deeper probing into edge cases warranted.",
            reasoning_evidence=["Explained architecture clearly", "Identified but did not address edge cases"],
            difficulty_direction="maintain",
            confidence="high",
        )
        mock_gen.return_value = mock_decision

        decision = engine.decide_next_action(
            candidate_profile=None,
            answer_analysis=analysis,
            answer_evaluation=evaluation,
            knowledge_state=knowledge_state,
            current_topic="Transformers",
        )

        assert decision.action == "DEEPEN"
        assert decision.confidence == "high"


def test_reasoning_engine_decides_clarify_for_incomplete_answer():
    """When answer is incomplete or vague, reasoning should suggest CLARIFY."""
    analysis = AnswerAnalysis(
        technical_correctness="unknown",
        demonstrated_concepts=[],
        missing_concepts=["model_evaluation", "validation_strategy"],
        incorrect_concepts=[],
        reasoning_quality="unclear",
        answer_relevance="medium",
        technical_depth="insufficient",
        completeness="incomplete",
        unsupported_claims=["Used best practices for evaluation"],
        resume_claim_relationships=[],
        recommended_actions=["clarify"],
        evidence=[],
    )
    evaluation = AnswerEvaluation(
        technical_correctness="partial",
        conceptual_understanding="weak",
        completeness="incomplete",
        technical_depth="shallow",
        reasoning_quality="weak",
        relevance="medium",
        application_ability="limited",
        confidence="low",
        evidence=[],
        gaps=["model evaluation", "validation"],
        strengths=[],
        unsupported_claims=["Used best practices"],
        uncertainty_notes=["Missing evidence limits assessment."],
    )
    knowledge_state = CandidateKnowledgeState(
        concept_states=[],
        summary="No concrete concept evidence was recorded yet.",
    )

    engine = InterviewReasoningEngine()
    with patch.object(engine.llm_client, "generate_structured") as mock_gen:
        mock_decision = InterviewDecision(
            action="CLARIFY",
            target_concept="model_evaluation",
            reasoning="Answer lacks detail on evaluation methodology. Clarification needed.",
            reasoning_evidence=["No evidence of evaluation approach", "Unsupported claim about best practices"],
            difficulty_direction="maintain",
            confidence="high",
        )
        mock_gen.return_value = mock_decision

        decision = engine.decide_next_action(
            candidate_profile=None,
            answer_analysis=analysis,
            answer_evaluation=evaluation,
            knowledge_state=knowledge_state,
            current_topic="Model Evaluation",
        )

        assert decision.action == "CLARIFY"


def test_reasoning_engine_decides_challenge_for_incorrect_answer():
    """When answer contains incorrect concepts, reasoning should suggest CHALLENGE."""
    analysis = AnswerAnalysis(
        technical_correctness="incorrect",
        demonstrated_concepts=[],
        missing_concepts=["optimization_algorithms"],
        incorrect_concepts=["gradient_descent", "learning_rate"],
        reasoning_quality="weak",
        answer_relevance="medium",
        technical_depth="shallow",
        completeness="incomplete",
        unsupported_claims=["Learning rate directly affects batch size"],
        resume_claim_relationships=[],
        recommended_actions=["challenge"],
        evidence=["Candidate conflated learning rate with batch size."],
    )
    evaluation = AnswerEvaluation(
        technical_correctness="weak",
        conceptual_understanding="weak",
        completeness="incomplete",
        technical_depth="shallow",
        reasoning_quality="weak",
        relevance="medium",
        application_ability="limited",
        confidence="high",
        evidence=["Confused learning rate and batch size concepts."],
        gaps=["optimization algorithms"],
        strengths=[],
        unsupported_claims=["Learning rate affects batch size"],
        uncertainty_notes=[],
    )
    knowledge_state = CandidateKnowledgeState(
        concept_states=[
            ConceptState(
                concept="gradient_descent",
                confidence="low",
                demonstrated=False,
                missing=False,
                incorrect=True,
                evidence=["Candidate confused learning rate with batch size."],
            )
        ],
        summary="Needs follow-up: gradient_descent.",
    )

    engine = InterviewReasoningEngine()
    with patch.object(engine.llm_client, "generate_structured") as mock_gen:
        mock_decision = InterviewDecision(
            action="CHALLENGE",
            target_concept="gradient_descent",
            reasoning="Candidate confused learning rate with batch size. Professional challenge to clarify understanding.",
            reasoning_evidence=["Conflated learning rate and batch size", "Incorrect conceptual model"],
            difficulty_direction="decrease",
            confidence="high",
        )
        mock_gen.return_value = mock_decision

        decision = engine.decide_next_action(
            candidate_profile=None,
            answer_analysis=analysis,
            answer_evaluation=evaluation,
            knowledge_state=knowledge_state,
            current_topic="Optimization",
        )

        assert decision.action == "CHALLENGE"
        assert decision.difficulty_direction == "decrease"


def test_interviewer_brain_orchestrator_makes_decision():
    """Orchestrator should integrate all components and produce a decision."""
    brain = InterviewerBrainOrchestrator("interview_456")

    candidate = CandidateProfile(
        identity=CandidateIdentity(full_name="Alice", email="alice@example.com"),
        skills=[],
        technologies=[],
        experience=[],
        projects=[],
        claims=[],
    )
    analysis = AnswerAnalysis(
        technical_correctness="correct",
        demonstrated_concepts=["concept_a"],
        missing_concepts=[],
        incorrect_concepts=[],
        reasoning_quality="strong",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="complete",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["probe_deeper"],
        evidence=["Clear explanation."],
    )
    evaluation = AnswerEvaluation(
        technical_correctness="strong",
        conceptual_understanding="strong",
        completeness="complete",
        technical_depth="moderate",
        reasoning_quality="strong",
        relevance="high",
        application_ability="strong",
        confidence="high",
        evidence=["Clear explanation."],
        gaps=[],
        strengths=["concept_a"],
        unsupported_claims=[],
        uncertainty_notes=[],
    )
    knowledge_state = CandidateKnowledgeState(
        concept_states=[
            ConceptState(
                concept="concept_a",
                confidence="high",
                demonstrated=True,
                missing=False,
                incorrect=False,
                evidence=["Clearly demonstrated."],
            )
        ],
        summary="Strong evidence for concept_a.",
    )

    with patch.object(InterviewReasoningEngine, "decide_next_action") as mock_reason:
        mock_decision = InterviewDecision(
            action="DEEPEN",
            target_concept="concept_a",
            reasoning="Strong foundation; deeper exploration warranted.",
            reasoning_evidence=["Strong technical understanding"],
            difficulty_direction="maintain",
            confidence="high",
        )
        mock_reason.return_value = mock_decision

        decision = brain.decide_next_action(
            candidate_profile=candidate,
            question="Explain concept_a.",
            candidate_answer="Concept_a is fundamental to...",
            answer_analysis=analysis,
            answer_evaluation=evaluation,
            knowledge_state=knowledge_state,
            current_topic="Fundamentals",
        )

        assert decision.action == "DEEPEN"
        assert brain.conversation_state.question_count == 1


def test_interviewer_brain_tracks_state_changes():
    """Orchestrator should update internal state based on decisions."""
    brain = InterviewerBrainOrchestrator("interview_789")

    brain.conversation_state.add_pending_claim(
        "claim-distributed", "Implemented distributed training"
    )
    assert brain.conversation_state.pending_claim_ids == ["claim-distributed"]
    assert "Implemented distributed training" in brain.conversation_state.pending_claims

    brain.mark_claim_investigated("claim-distributed")
    assert brain.conversation_state.pending_claim_ids == []
    assert "Implemented distributed training" not in brain.conversation_state.pending_claims

    brain.conversation_state.add_unresolved_gap("No details on fault tolerance")
    assert "No details on fault tolerance" in brain.conversation_state.unresolved_gaps

    brain.mark_gap_resolved("No details on fault tolerance")
    assert "No details on fault tolerance" not in brain.conversation_state.unresolved_gaps
