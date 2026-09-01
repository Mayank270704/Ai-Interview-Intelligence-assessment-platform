"""Tests for the Interview Turn Orchestrator V1."""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import InterviewPipelineError
from app.schemas.answer import AnswerAnalysis, ResumeClaimRelationship
from app.schemas.interview_decision import InterviewDecision
from app.schemas.question import GeneratedQuestion
from app.schemas.resume import CandidateIdentity, CandidateProfile, Claim, Skill
from app.services.interview.turn_service import InterviewTurnService


ACCURACY_CLAIM = "Improved model accuracy by 18%"
TEAM_CLAIM = "Led a team of six engineers"


def _claim(text: str) -> Claim:
    return Claim(claim_text=text, category="quantitative", resume_evidence=f"{text}.")


def _profile(claim_texts: list[str] | None = None) -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe"),
        professional_summary="Machine Learning Engineer with 5 years of experience",
        skills=[Skill(name="Machine Learning")],
        claims=[_claim(text) for text in (claim_texts or [ACCURACY_CLAIM, TEAM_CLAIM])],
    )


def _question(
    text: str = "How did you approach the sentiment model?",
    target_concept: str = "Machine Learning",
    intent: str = "EXPLORE_RELATED_CONCEPT",
    difficulty: str = "medium",
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question=text,
        target_concept=target_concept,
        difficulty=difficulty,
        intent=intent,
        evaluation_focus=["model training"],
    )


def _analysis() -> AnswerAnalysis:
    return AnswerAnalysis(
        technical_correctness="partially_correct",
        demonstrated_concepts=["fine_tuning"],
        missing_concepts=["tokenization"],
        incorrect_concepts=[],
        reasoning_quality="adequate",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["probe_deeper"],
        evidence=["Candidate described the fine-tuning loop."],
    )


def _decision(
    action: str = "DEEPEN",
    target_concept: str = "tokenization",
    difficulty_direction: str = "maintain",
) -> InterviewDecision:
    return InterviewDecision(
        action=action,
        target_concept=target_concept,
        reasoning="Tokenization remains under-evidenced.",
        reasoning_evidence=["No tokenizer named"],
        difficulty_direction=difficulty_direction,
        confidence="medium",
    )


def _service(
    difficulty: str = "medium", profile: CandidateProfile | None = None
) -> InterviewTurnService:
    """Build a service whose LLM-backed components are mocked."""
    service = InterviewTurnService(
        interview_id="interview_1",
        interview_objective="Machine Learning",
        candidate_profile=profile or _profile(),
        difficulty=difficulty,
    )
    service.question_generator.generate_question = MagicMock(return_value=_question())
    service.answer_analyzer.llm_client = MagicMock()
    service.answer_analyzer.llm_client.generate_structured.return_value = _analysis()
    service.brain.reasoning_engine.decide_next_action = MagicMock(
        return_value=_decision()
    )
    return service


def _started_service(
    difficulty: str = "medium", profile: CandidateProfile | None = None
) -> InterviewTurnService:
    service = _service(difficulty, profile)
    service.start_interview()
    service.question_generator.generate_question.reset_mock()
    return service


def _claim_analysis(
    claim_text: str,
    relationship: str,
    claim_evidence: str | None = None,
    answer_evidence: list[str] | None = None,
) -> AnswerAnalysis:
    """Build an analysis that relates the answer to one resume claim."""
    analysis = _analysis()
    analysis.evidence = (
        answer_evidence
        if answer_evidence is not None
        else ["Candidate described the fine-tuning loop."]
    )
    analysis.resume_claim_relationships = [
        ResumeClaimRelationship(
            claim_text=claim_text,
            relationship=relationship,
            evidence=claim_evidence,
        )
    ]
    return analysis


def test_requires_an_interview_objective():
    """An interview cannot start without an objective to investigate."""
    with pytest.raises(ValueError, match="interview objective is required"):
        InterviewTurnService(interview_id="interview_1", interview_objective="   ")


def test_first_question_is_generated_from_objective_and_candidate_context():
    """The opening question comes from the objective and candidate context, not a prior answer."""
    service = _service()

    question = service.start_interview()

    assert question.question
    assert service.current_question is question
    kwargs = service.question_generator.generate_question.call_args.kwargs
    assert kwargs["decision"].target_concept == "Machine Learning"
    assert kwargs["decision"].action == "EXPLORE_RELATED_CONCEPT"
    assert kwargs["candidate_profile"] is service.candidate_profile
    assert kwargs["difficulty"] == "medium"
    assert service.brain.conversation_state.current_topic == question.target_concept


def test_first_turn_does_not_run_answer_or_decision_components():
    """No answer intelligence or brain reasoning may run before the first answer."""
    service = _service()

    service.start_interview()

    service.answer_analyzer.llm_client.generate_structured.assert_not_called()
    service.brain.reasoning_engine.decide_next_action.assert_not_called()


def test_start_interview_cannot_generate_a_second_opening_question():
    """Starting an already started interview must not produce a duplicate question."""
    service = _service()
    service.start_interview()

    with pytest.raises(ValueError, match="already produced a question"):
        service.start_interview()

    assert service.question_generator.generate_question.call_count == 1


def test_submit_answer_requires_a_pending_question():
    """An answer cannot be processed before a question has been asked."""
    service = _service()

    with pytest.raises(ValueError, match="no pending question"):
        service.submit_answer("Some answer.")


def test_subsequent_turn_runs_the_full_pipeline():
    """Answer analysis, evaluation, knowledge update, brain, and generation all run once."""
    service = _started_service()
    asked = service.current_question
    next_question = _question(
        "Which tokenizer did you use?", target_concept="tokenization", intent="DEEPEN"
    )
    service.question_generator.generate_question.return_value = next_question

    result = service.submit_answer("I fine-tuned BERT on support tickets.")

    assert result is next_question
    assert service.current_question is next_question

    analyzer_prompt = service.answer_analyzer.llm_client.generate_structured.call_args[0][0]
    assert asked.question in analyzer_prompt

    assert service.brain.reasoning_engine.decide_next_action.call_count == 1
    assert service.question_generator.generate_question.call_count == 1

    kwargs = service.question_generator.generate_question.call_args.kwargs
    assert kwargs["answer_evaluation"] is not None
    assert kwargs["answer_evaluation"].technical_correctness == "moderate"
    assert kwargs["knowledge_state"] is service.knowledge_state


def test_evaluation_and_knowledge_state_feed_the_brain():
    """Evaluation output and the updated knowledge state must reach the Interviewer Brain."""
    service = _started_service()

    service.submit_answer("I fine-tuned BERT on support tickets.")

    brain_kwargs = service.brain.reasoning_engine.decide_next_action.call_args.kwargs
    assert brain_kwargs["answer_analysis"].demonstrated_concepts == ["fine_tuning"]
    assert brain_kwargs["answer_evaluation"].technical_correctness == "moderate"
    assert brain_kwargs["knowledge_state"] is service.knowledge_state

    concepts = {entry.concept for entry in service.knowledge_state.concept_states}
    assert concepts == {"fine_tuning", "tokenization"}


def test_knowledge_state_accumulates_across_turns():
    """The service must carry the accumulated knowledge state into each turn's update."""
    service = _started_service()
    second_analysis = _analysis()
    second_analysis.demonstrated_concepts = ["tokenization"]
    second_analysis.missing_concepts = ["evaluation_metrics"]
    service.answer_analyzer.llm_client.generate_structured.side_effect = [
        _analysis(),
        second_analysis,
    ]

    service.submit_answer("First answer.")
    service.submit_answer("Second answer.")

    concepts = {entry.concept: entry for entry in service.knowledge_state.concept_states}
    assert set(concepts) == {"fine_tuning", "tokenization", "evaluation_metrics"}
    assert concepts["fine_tuning"].demonstrated
    assert concepts["tokenization"].demonstrated
    assert not concepts["tokenization"].missing


def test_resume_claims_are_verified_and_accumulated_through_the_service():
    """The service must pass the candidate's claims and retain the accumulated verifications."""
    service = _started_service()
    claim_text = "Improved model accuracy by 18%"
    first_analysis = _analysis()
    first_analysis.resume_claim_relationships = [
        ResumeClaimRelationship(
            claim_text=claim_text,
            relationship="supports",
            evidence="Reported an 18% lift on the validation set.",
        )
    ]
    second_analysis = _analysis()
    second_analysis.resume_claim_relationships = [
        ResumeClaimRelationship(
            claim_text=claim_text,
            relationship="supports",
            evidence="Described the baseline the 18% was measured against.",
        )
    ]
    service.answer_analyzer.llm_client.generate_structured.side_effect = [
        first_analysis,
        second_analysis,
    ]

    service.submit_answer("We measured against the baseline.")
    after_first = service.knowledge_state.claim_verifications
    assert [entry.claim_text for entry in after_first] == [claim_text]
    assert after_first[0].status == "supported"

    service.submit_answer("The baseline was the previous production model.")
    verifications = service.knowledge_state.claim_verifications
    assert len(verifications) == 1
    assert verifications[0].confidence == "high"
    assert "Reported an 18% lift on the validation set." in verifications[0].evidence
    assert (
        "Described the baseline the 18% was measured against."
        in verifications[0].evidence
    )

    brain_kwargs = service.brain.reasoning_engine.decide_next_action.call_args.kwargs
    assert brain_kwargs["knowledge_state"] is service.knowledge_state


def test_resume_claims_are_seeded_into_pending_claims():
    """Every resume claim starts pending so the brain can choose to investigate it."""
    service = _service()

    assert service.brain.conversation_state.pending_claims == [
        ACCURACY_CLAIM,
        TEAM_CLAIM,
    ]


def test_seeding_does_not_duplicate_claims():
    """A repeated resume claim must be tracked once."""
    service = _service(profile=_profile([ACCURACY_CLAIM, ACCURACY_CLAIM]))

    assert service.brain.conversation_state.pending_claims == [ACCURACY_CLAIM]


def test_sufficiently_supported_claim_is_resolved():
    """A claim supported by enough accumulated evidence stops being pending."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.return_value = _claim_analysis(
        ACCURACY_CLAIM,
        "supports",
        claim_evidence="Reported an 18% lift on the validation set.",
    )

    service.submit_answer("We measured an 18% lift against the baseline.")

    pending = service.brain.conversation_state.pending_claims
    assert ACCURACY_CLAIM not in pending
    assert TEAM_CLAIM in pending


def test_mentioned_claim_with_thin_evidence_stays_pending():
    """Mentioning a claim is not by itself sufficient evidence to resolve it."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.return_value = _claim_analysis(
        ACCURACY_CLAIM, "supports", claim_evidence=None, answer_evidence=[]
    )

    service.submit_answer("Yes, accuracy went up by 18%.")

    verification = service.knowledge_state.claim_verifications[0]
    assert verification.status == "supported"
    assert verification.confidence == "medium"
    assert ACCURACY_CLAIM in service.brain.conversation_state.pending_claims


def test_uncertain_claim_remains_pending():
    """A claim the answer only touches on remains open for investigation."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.return_value = _claim_analysis(
        ACCURACY_CLAIM, "clarifies", claim_evidence="Talked around the measurement."
    )

    service.submit_answer("It was roughly an 18% improvement, I think.")

    assert service.knowledge_state.claim_verifications[0].status == "uncertain"
    assert ACCURACY_CLAIM in service.brain.conversation_state.pending_claims


def test_conflicting_claim_returns_to_pending_with_evidence_preserved():
    """A resolved claim that a later answer contradicts must reopen, keeping both sides."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.side_effect = [
        _claim_analysis(
            ACCURACY_CLAIM,
            "supports",
            claim_evidence="Reported an 18% lift on the validation set.",
        ),
        _claim_analysis(
            ACCURACY_CLAIM,
            "contradicts",
            claim_evidence="Could not say how the 18% was measured.",
        ),
    ]

    service.submit_answer("We measured an 18% lift against the baseline.")
    assert ACCURACY_CLAIM not in service.brain.conversation_state.pending_claims

    service.submit_answer("I am not sure how it was measured.")

    verification = service.knowledge_state.claim_verifications[0]
    assert verification.status == "unsupported"
    assert "Reported an 18% lift on the validation set." in verification.evidence
    assert "Could not say how the 18% was measured." in verification.evidence
    assert ACCURACY_CLAIM in service.brain.conversation_state.pending_claims


def test_unmentioned_claim_is_never_resolved():
    """A claim no answer addresses stays pending and unverified."""
    service = _started_service()

    service.submit_answer("First answer.")
    service.submit_answer("Second answer.")

    assert service.knowledge_state.claim_verifications == []
    assert service.brain.conversation_state.pending_claims == [
        ACCURACY_CLAIM,
        TEAM_CLAIM,
    ]


def test_claims_are_tracked_independently_across_turns():
    """Resolving one claim must not affect the state of another."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.side_effect = [
        _claim_analysis(
            ACCURACY_CLAIM,
            "supports",
            claim_evidence="Reported an 18% lift on the validation set.",
        ),
        _claim_analysis(
            TEAM_CLAIM,
            "clarifies",
            claim_evidence="Described the team without stating its size.",
        ),
    ]

    service.submit_answer("We measured an 18% lift against the baseline.")
    service.submit_answer("I worked with a few other engineers.")

    statuses = {
        entry.claim_text: entry.status
        for entry in service.knowledge_state.claim_verifications
    }
    assert statuses[ACCURACY_CLAIM] == "supported"
    assert statuses[TEAM_CLAIM] == "uncertain"
    assert service.brain.conversation_state.pending_claims == [TEAM_CLAIM]


def test_brain_receives_the_updated_pending_claims():
    """The Interviewer Brain must reason over the current pending claims."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.return_value = _claim_analysis(
        ACCURACY_CLAIM,
        "supports",
        claim_evidence="Reported an 18% lift on the validation set.",
    )

    service.submit_answer("We measured an 18% lift against the baseline.")

    brain_kwargs = service.brain.reasoning_engine.decide_next_action.call_args.kwargs
    assert brain_kwargs["pending_claims"] == [TEAM_CLAIM]


def test_decision_is_propagated_into_the_question_generator():
    """The Interviewer Brain's decision must be the decision the Question Engine receives."""
    service = _started_service()
    decision = _decision(action="CHALLENGE", target_concept="gradient_descent")
    service.brain.reasoning_engine.decide_next_action.return_value = decision

    service.submit_answer("Learning rate sets the batch size.")

    kwargs = service.question_generator.generate_question.call_args.kwargs
    assert kwargs["decision"] is decision


def test_difficulty_follows_the_decided_direction():
    """Difficulty direction is applied to the current level and passed to the generator."""
    service = _started_service(difficulty="medium")
    service.brain.reasoning_engine.decide_next_action.return_value = _decision(
        difficulty_direction="increase"
    )

    service.submit_answer("Detailed and correct answer.")

    assert service.difficulty == "hard"
    assert service.question_generator.generate_question.call_args.kwargs["difficulty"] == "hard"

    service.brain.reasoning_engine.decide_next_action.return_value = _decision(
        difficulty_direction="increase"
    )
    service.submit_answer("Another strong answer.")
    assert service.difficulty == "hard"

    service.brain.reasoning_engine.decide_next_action.return_value = _decision(
        difficulty_direction="decrease"
    )
    service.submit_answer("A weaker answer.")
    assert service.difficulty == "medium"
    assert service.question_generator.generate_question.call_args.kwargs["difficulty"] == "medium"


def test_interview_state_continues_across_turns():
    """Conversation state accumulates turns and is passed back into question generation."""
    service = _started_service()
    first_question = service.current_question

    service.submit_answer("First answer.")
    service.submit_answer("Second answer.")

    state = service.brain.get_interview_state()
    assert state["question_count"] == 2
    assert state["interview_id"] == "interview_1"

    kwargs = service.question_generator.generate_question.call_args.kwargs
    recent_questions = [turn["question"] for turn in kwargs["recent_turns"]]
    assert first_question.question in recent_questions
    assert kwargs["explored_concepts"] == list(
        service.brain.conversation_state.explored_concepts
    )


def test_answer_intelligence_failure_propagates():
    """A failure in Answer Intelligence must not be swallowed or replaced by a fallback."""
    service = _started_service()
    service.answer_analyzer.llm_client.generate_structured.side_effect = RuntimeError(
        "LLM unavailable"
    )

    with pytest.raises(InterviewPipelineError, match="Failed to analyze answer"):
        service.submit_answer("An answer.")

    service.question_generator.generate_question.assert_not_called()


def test_interviewer_brain_failure_propagates():
    """A failure in the Interviewer Brain must stop the turn."""
    service = _started_service()
    service.brain.reasoning_engine.decide_next_action.side_effect = ValueError(
        "Failed to reason about next action"
    )

    with pytest.raises(InterviewPipelineError, match="Failed to reason about next action"):
        service.submit_answer("An answer.")

    service.question_generator.generate_question.assert_not_called()


def test_question_generation_failure_propagates_and_keeps_pending_question():
    """A generation failure must surface and must not leave an invented question behind."""
    service = _started_service()
    asked = service.current_question
    service.question_generator.generate_question.side_effect = ValueError(
        "Failed to generate question"
    )

    with pytest.raises(InterviewPipelineError, match="Failed to generate question"):
        service.submit_answer("An answer.")

    assert service.current_question is asked
