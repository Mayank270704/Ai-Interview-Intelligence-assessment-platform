"""Tests for the Question Engine V1."""

from unittest.mock import MagicMock

import pytest

from app.ai.question_engine.generator import QuestionGenerator
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge import RetrievedKnowledge
from app.schemas.knowledge_state import CandidateKnowledgeState, ConceptState
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import (
    CandidateIdentity,
    CandidateProfile,
    Claim,
    Project,
    Skill,
)


def _generator_with_response(question: GeneratedQuestion) -> QuestionGenerator:
    """Build a generator whose LLM client is mocked with a fixed structured response."""
    generator = QuestionGenerator()
    generator.llm_client = MagicMock()
    generator.llm_client.generate_structured.return_value = question
    return generator


def _prompt_of(generator: QuestionGenerator) -> str:
    """Return the prompt passed to the mocked LLM client."""
    return generator.llm_client.generate_structured.call_args[0][0]


def _response(
    question: str,
    target_concept: str,
    intent: str = "DEEPEN",
    difficulty: str = "medium",
    evaluation_focus: list[str] | None = None,
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question=question,
        target_concept=target_concept,
        difficulty=difficulty,
        intent=intent,
        evaluation_focus=evaluation_focus or [],
    )


def _profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe"),
        professional_summary="Machine Learning Engineer with 5 years of experience",
        skills=[Skill(name="Machine Learning"), Skill(name="Python")],
        projects=[
            Project(
                name="BERT Sentiment Analysis",
                description="Built a sentiment analysis system for support tickets",
                technologies=["BERT", "PyTorch"],
            )
        ],
        claims=[
            Claim(
                claim_text="Improved model accuracy by 18%",
                category="quantitative",
                context="Sentiment analysis project",
                resume_evidence="Improved model accuracy by 18%",
            )
        ],
    )


def _evaluation() -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_correctness="moderate",
        conceptual_understanding="moderate",
        completeness="partial",
        technical_depth="shallow",
        reasoning_quality="moderate",
        relevance="high",
        application_ability="moderate",
        confidence="medium",
        evidence=["Candidate described fine-tuning at a high level."],
        gaps=["tokenization strategy"],
        strengths=["fine-tuning workflow"],
        unsupported_claims=[],
        uncertainty_notes=[],
    )


def test_generates_deepen_question_from_decision():
    """A DEEPEN decision should produce a question probing the mechanism."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="attention_mechanism",
        reasoning="Candidate explained attention at a high level only.",
        reasoning_evidence=["No mention of scaled dot-product computation"],
        difficulty_direction="maintain",
        confidence="high",
    )
    generator = _generator_with_response(
        _response(
            "Walk me through how scaled dot-product attention actually computes its weights.",
            "attention_mechanism",
            intent="DEEPEN",
        )
    )

    result = generator.generate_question(
        decision=decision,
        difficulty="medium",
        answer_evaluation=_evaluation(),
    )

    assert result.intent == "DEEPEN"
    assert result.target_concept == "attention_mechanism"
    assert result.difficulty == "medium"
    prompt = _prompt_of(generator)
    assert "Action: DEEPEN" in prompt
    assert "attention_mechanism" in prompt
    assert "tokenization strategy" in prompt


def test_generates_clarify_question_for_vague_answer():
    """A CLARIFY decision should carry the ambiguity into the prompt."""
    decision = InterviewDecision(
        action="CLARIFY",
        target_concept="model_evaluation",
        reasoning="Candidate referred to best practices without specifying metrics.",
        reasoning_evidence=["No evaluation metric named"],
        difficulty_direction="maintain",
        confidence="medium",
    )
    generator = _generator_with_response(
        _response(
            "Which metrics did you use to evaluate the model, and why those?",
            "model_evaluation",
            intent="CLARIFY",
        )
    )

    result = generator.generate_question(decision=decision, difficulty="medium")

    assert result.intent == "CLARIFY"
    prompt = _prompt_of(generator)
    assert "Action: CLARIFY" in prompt
    assert "No evaluation metric named" in prompt


def test_generates_challenge_question_with_evidence():
    """A CHALLENGE decision should pass the contested evidence to the LLM."""
    decision = InterviewDecision(
        action="CHALLENGE",
        target_concept="gradient_descent",
        reasoning="Candidate claimed the learning rate determines batch size.",
        reasoning_evidence=["Conflated learning rate with batch size"],
        difficulty_direction="decrease",
        confidence="high",
    )
    generator = _generator_with_response(
        _response(
            "You mentioned the learning rate sets the batch size - can you take me through that reasoning?",
            "gradient_descent",
            intent="CHALLENGE",
        )
    )

    result = generator.generate_question(
        decision=decision,
        difficulty="easy",
        answer_evaluation=_evaluation(),
    )

    assert result.intent == "CHALLENGE"
    assert result.difficulty == "easy"
    prompt = _prompt_of(generator)
    assert "Action: CHALLENGE" in prompt
    assert "Conflated learning rate with batch size" in prompt


def test_generates_investigate_claim_question_grounded_in_resume():
    """An INVESTIGATE_CLAIM decision should ground the prompt in resume evidence."""
    decision = InterviewDecision(
        action="INVESTIGATE_CLAIM",
        target_concept="model_accuracy_improvement",
        reasoning="The 18% accuracy claim has not been verified.",
        reasoning_evidence=["Claim still pending verification"],
        difficulty_direction="maintain",
        resume_claim_to_investigate="Improved model accuracy by 18%",
        confidence="high",
    )
    generator = _generator_with_response(
        _response(
            "Your resume mentions an 18% accuracy improvement - what changed to produce it?",
            "model_accuracy_improvement",
            intent="INVESTIGATE_CLAIM",
        )
    )

    result = generator.generate_question(
        decision=decision,
        difficulty="medium",
        candidate_profile=_profile(),
    )

    assert result.intent == "INVESTIGATE_CLAIM"
    prompt = _prompt_of(generator)
    assert "Resume claim to investigate: Improved model accuracy by 18%" in prompt
    assert "BERT Sentiment Analysis" in prompt
    assert "Never invent candidate experience" in prompt


def test_resume_context_contains_only_resume_facts():
    """The candidate context should reproduce resume facts without adding new ones."""
    generator = QuestionGenerator()
    context = generator._build_candidate_context(_profile())

    assert "Machine Learning Engineer with 5 years of experience" in context
    assert "BERT Sentiment Analysis" in context
    assert "Improved model accuracy by 18%" in context
    assert "Experience:" not in context


def test_generates_increase_difficulty_question_at_requested_difficulty():
    """The requested difficulty must be honored in the prompt and the result."""
    decision = InterviewDecision(
        action="INCREASE_DIFFICULTY",
        target_concept="distributed_training",
        reasoning="Candidate demonstrated mastery of single-node training.",
        reasoning_evidence=["Explained data loading and checkpointing correctly"],
        difficulty_direction="increase",
        confidence="high",
    )
    generator = _generator_with_response(
        _response(
            "How would you shard a model that no longer fits on one GPU?",
            "distributed_training",
            intent="INCREASE_DIFFICULTY",
            difficulty="medium",
        )
    )

    result = generator.generate_question(decision=decision, difficulty="hard")

    assert result.difficulty == "hard"
    assert result.intent == "INCREASE_DIFFICULTY"
    assert "Required difficulty: hard" in _prompt_of(generator)


def test_generates_change_topic_question_using_next_topic():
    """CHANGE_TOPIC should target the decision's next topic."""
    decision = InterviewDecision(
        action="CHANGE_TOPIC",
        target_concept="transformers",
        reasoning="Transformers are sufficiently explored; system design remains unassessed.",
        reasoning_evidence=["Three consistent transformer answers"],
        difficulty_direction="maintain",
        next_topic="system_design",
        confidence="medium",
    )
    generator = _generator_with_response(
        _response(
            "Let us switch gears - how would you design a serving layer for a model like that?",
            "transformers",
            intent="CHANGE_TOPIC",
        )
    )

    result = generator.generate_question(decision=decision, difficulty="medium")

    assert result.intent == "CHANGE_TOPIC"
    assert result.target_concept == "system_design"
    assert "Target concept: system_design" in _prompt_of(generator)


def test_avoids_repeating_explored_concepts_and_recent_turns():
    """Explored concepts and recent turns must be supplied so questions are not repeated."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="tokenization",
        reasoning="Tokenization remains under-evidenced.",
        reasoning_evidence=["No tokenizer named"],
        difficulty_direction="maintain",
        confidence="medium",
    )
    generator = _generator_with_response(
        _response("Which tokenizer did you use, and how did it handle rare terms?", "tokenization")
    )

    generator.generate_question(
        decision=decision,
        difficulty="medium",
        recent_turns=[
            {
                "question": "Explain the transformer architecture.",
                "answer": "It uses self-attention over token embeddings.",
            }
        ],
        explored_concepts=["transformer_architecture", "attention_mechanism"],
    )

    prompt = _prompt_of(generator)
    assert "transformer_architecture, attention_mechanism" in prompt
    assert "Explain the transformer architecture." in prompt
    assert "do not revisit an already" in prompt


def test_uses_supplied_retrieved_knowledge_as_context():
    """Retrieved knowledge supplied by the caller should be used as context."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="vector_search",
        reasoning="Candidate mentioned approximate search without detail.",
        reasoning_evidence=["No index type named"],
        difficulty_direction="maintain",
        confidence="medium",
    )
    generator = _generator_with_response(
        _response("How does HNSW trade recall against latency in your setup?", "vector_search")
    )

    generator.generate_question(
        decision=decision,
        difficulty="medium",
        retrieved_knowledge=[
            RetrievedKnowledge(
                id="doc-1:0",
                title="HNSW indexes",
                content="HNSW builds a navigable small-world graph for approximate nearest neighbour search.",
                source="internal_knowledge",
                score=0.87,
            )
        ],
    )

    prompt = _prompt_of(generator)
    assert "[internal_knowledge] HNSW indexes" in prompt
    assert "navigable small-world graph" in prompt


def test_knowledge_state_evidence_is_included():
    """Knowledge state evidence should reach the prompt when provided."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="backpropagation",
        reasoning="Partial evidence for backpropagation.",
        reasoning_evidence=["Chain rule mentioned but not applied"],
        difficulty_direction="maintain",
        confidence="medium",
    )
    generator = _generator_with_response(
        _response("Walk me through the gradient flow in that network.", "backpropagation")
    )

    generator.generate_question(
        decision=decision,
        difficulty="medium",
        knowledge_state=CandidateKnowledgeState(
            concept_states=[
                ConceptState(
                    concept="backpropagation",
                    confidence="medium",
                    demonstrated=True,
                    evidence=["Mentioned the chain rule."],
                )
            ],
            summary="Partial evidence for backpropagation.",
        ),
    )

    prompt = _prompt_of(generator)
    assert "backpropagation: confidence=medium" in prompt
    assert "Summary: Partial evidence for backpropagation." in prompt


def test_llm_failure_raises_value_error():
    """A failing or unparsable LLM response must surface as a ValueError."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="caching",
        reasoning="Needs deeper probing.",
        difficulty_direction="maintain",
        confidence="medium",
    )
    generator = QuestionGenerator()
    generator.llm_client = MagicMock()
    generator.llm_client.generate_structured.side_effect = ValueError(
        "Failed to parse response as GeneratedQuestion"
    )

    with pytest.raises(ValueError, match="Failed to generate question"):
        generator.generate_question(decision=decision, difficulty="medium")


def test_blank_generated_question_is_rejected():
    """A structurally valid but empty question must be rejected."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="caching",
        reasoning="Needs deeper probing.",
        difficulty_direction="maintain",
        confidence="medium",
    )
    generator = _generator_with_response(_response("   ", "caching"))

    with pytest.raises(ValueError, match="Generated question is empty"):
        generator.generate_question(decision=decision, difficulty="medium")


def test_missing_target_concept_raises_before_llm_call():
    """A decision without a target concept cannot produce a grounded question."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="   ",
        reasoning="No concept recorded.",
        difficulty_direction="maintain",
        confidence="low",
    )
    generator = _generator_with_response(_response("Anything?", "unknown"))

    with pytest.raises(ValueError, match="no target concept"):
        generator.generate_question(decision=decision, difficulty="medium")

    generator.llm_client.generate_structured.assert_not_called()


def test_investigate_claim_without_any_claim_raises():
    """Claim investigation without an available claim must not be invented."""
    decision = InterviewDecision(
        action="INVESTIGATE_CLAIM",
        target_concept="model_accuracy_improvement",
        reasoning="A claim should be verified.",
        difficulty_direction="maintain",
        confidence="low",
    )
    generator = _generator_with_response(
        _response("Tell me about your accuracy work.", "model_accuracy_improvement")
    )

    with pytest.raises(ValueError, match="no resume claim is available"):
        generator.generate_question(
            decision=decision,
            difficulty="medium",
            candidate_profile=CandidateProfile(identity=CandidateIdentity()),
        )

    generator.llm_client.generate_structured.assert_not_called()


def test_missing_optional_context_still_generates_question():
    """With only a decision, generation should still work and say what is absent."""
    decision = InterviewDecision(
        action="DEEPEN",
        target_concept="indexing",
        reasoning="First question on this topic.",
        difficulty_direction="maintain",
        confidence="low",
    )
    generator = _generator_with_response(
        _response("How do you decide which columns to index?", "indexing")
    )

    result = generator.generate_question(decision=decision, difficulty="medium")

    assert result.question
    prompt = _prompt_of(generator)
    assert "No candidate profile available." in prompt
    assert "No previous conversation turns." in prompt
    assert "No retrieved knowledge was supplied." in prompt
    assert "No evaluation of a previous answer is available." in prompt
