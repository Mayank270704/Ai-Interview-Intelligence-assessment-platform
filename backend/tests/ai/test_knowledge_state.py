"""Tests for candidate knowledge state and resume-claim verification."""

from app.ai.knowledge_intelligence.knowledge_state import KnowledgeStateTracker
from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.resume import Claim


def test_candidate_knowledge_state_tracks_demonstrated_and_missing_concepts():
    """The state tracker should accumulate evidence for concepts and note missing ones."""
    analysis = AnswerAnalysis(
        technical_correctness="correct",
        demonstrated_concepts=["transformer architecture", "fine-tuning"],
        missing_concepts=["evaluation metrics"],
        incorrect_concepts=[],
        reasoning_quality="strong",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=[],
        resume_claim_relationships=[],
        recommended_actions=["probe_deeper"],
        evidence=[
            "Explained the transformer encoder-decoder stack.",
            "Described how fine-tuning adjusted the last layer.",
        ],
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
        gaps=["evaluation metrics"],
        strengths=["transformer architecture", "fine-tuning"],
        unsupported_claims=[],
        uncertainty_notes=[],
    )

    tracker = KnowledgeStateTracker()
    state = tracker.update_from_answer(
        question="How did you adapt the model for the classification task?",
        answer="I used a transformer encoder and fine-tuned the final layer on labeled data.",
        answer_analysis=analysis,
        answer_evaluation=evaluation,
    )

    concept_map = {entry.concept: entry for entry in state.concept_states}
    assert "transformer architecture" in concept_map
    assert concept_map["transformer architecture"].confidence == "high"
    assert concept_map["evaluation metrics"].confidence == "low"
    assert state.summary


def test_resume_claim_verification_marks_claims_as_supported_or_uncertain():
    """Claims should be evaluated using answer evidence and the current interview state."""
    claim = Claim(
        claim_text="Improved model accuracy by 18%",
        category="quantitative",
        context="Sentiment analysis project",
        resume_evidence="Improved model accuracy by 18%.",
    )
    analysis = AnswerAnalysis(
        technical_correctness="correct",
        demonstrated_concepts=["model evaluation"],
        missing_concepts=[],
        incorrect_concepts=[],
        reasoning_quality="strong",
        answer_relevance="high",
        technical_depth="moderate",
        completeness="complete",
        unsupported_claims=[],
        resume_claim_relationships=[
            {
                "claim_text": "Improved model accuracy by 18%",
                "relationship": "supports",
                "evidence": "Compared against the baseline model and observed a 18% lift in validation accuracy.",
            }
        ],
        recommended_actions=["investigate_resume_claim"],
        evidence=[
            "Compared the baseline and final models on the validation set.",
            "Reported an 18% lift in validation accuracy.",
        ],
    )

    tracker = KnowledgeStateTracker()
    verification = tracker.verify_resume_claim(claim, answer_analysis=analysis)

    assert verification.status == "supported"
    assert verification.confidence in {"medium", "high"}
    assert "18%" in " ".join(verification.evidence)

    unsupported_analysis = AnswerAnalysis(
        technical_correctness="unknown",
        demonstrated_concepts=[],
        missing_concepts=["validation strategy"],
        incorrect_concepts=["baseline comparison"],
        reasoning_quality="unclear",
        answer_relevance="low",
        technical_depth="insufficient",
        completeness="incomplete",
        unsupported_claims=["Improved model accuracy by 18%"],
        resume_claim_relationships=[],
        recommended_actions=["challenge"],
        evidence=[],
    )
    unresolved = tracker.verify_resume_claim(claim, answer_analysis=unsupported_analysis)
    assert unresolved.status in {"unsupported", "uncertain"}


def _analysis(
    demonstrated: list[str] | None = None,
    missing: list[str] | None = None,
    incorrect: list[str] | None = None,
    evidence: list[str] | None = None,
    reasoning_quality: str = "strong",
    unsupported_claims: list[str] | None = None,
    claim_relationships: list[dict] | None = None,
    concept_evidence: list[dict] | None = None,
) -> AnswerAnalysis:
    """Build an answer analysis for a single interview turn."""
    return AnswerAnalysis(
        technical_correctness="correct" if not incorrect else "incorrect",
        demonstrated_concepts=demonstrated or [],
        missing_concepts=missing or [],
        incorrect_concepts=incorrect or [],
        reasoning_quality=reasoning_quality,
        answer_relevance="high",
        technical_depth="moderate",
        completeness="partial",
        unsupported_claims=unsupported_claims or [],
        resume_claim_relationships=claim_relationships or [],
        recommended_actions=["probe_deeper"],
        concept_evidence=concept_evidence or [],
        evidence=evidence or [],
    )


def _update(tracker, analysis, current_state=None, resume_claims=None):
    return tracker.update_from_answer(
        question="Tell me more.",
        answer="An answer.",
        answer_analysis=analysis,
        current_state=current_state,
        resume_claims=resume_claims,
    )


def test_evidence_accumulates_across_interview_turns():
    """Concepts from earlier turns must survive later turns that never mention them."""
    tracker = KnowledgeStateTracker()

    first = _update(
        tracker,
        _analysis(
            demonstrated=["attention"],
            missing=["tokenization"],
            evidence=["Explained scaled dot-product attention."],
        ),
    )
    second = _update(
        tracker,
        _analysis(
            demonstrated=["tokenization"],
            evidence=["Described the WordPiece vocabulary."],
        ),
        current_state=first,
    )

    concepts = {entry.concept: entry for entry in second.concept_states}
    assert set(concepts) == {"attention", "tokenization"}
    assert concepts["attention"].demonstrated
    assert concepts["attention"].evidence == ["Explained scaled dot-product attention."]
    assert concepts["tokenization"].demonstrated
    assert not concepts["tokenization"].missing
    assert "Described the WordPiece vocabulary." in concepts["tokenization"].evidence


def test_multiple_evidence_items_accumulate_for_the_same_concept():
    """Repeated demonstration of one concept should collect evidence and corroborate confidence."""
    tracker = KnowledgeStateTracker()

    first = _update(
        tracker,
        _analysis(
            demonstrated=["caching"],
            evidence=["Described a write-through cache."],
            reasoning_quality="weak",
        ),
    )
    assert first.concept_states[0].confidence == "medium"

    second = _update(
        tracker,
        _analysis(
            demonstrated=["caching"],
            evidence=["Explained cache invalidation trade-offs."],
        ),
        current_state=first,
    )

    caching = second.concept_states[0]
    assert caching.concept == "caching"
    assert caching.confidence == "high"
    assert caching.evidence == [
        "Described a write-through cache.",
        "Explained cache invalidation trade-offs.",
    ]


def test_weak_later_answer_does_not_erase_strong_earlier_evidence():
    """A later turn that omits a demonstrated concept must not erase the earlier evidence."""
    tracker = KnowledgeStateTracker()

    first = _update(
        tracker,
        _analysis(
            demonstrated=["backpropagation"],
            evidence=["Derived the gradient update step by step."],
        ),
    )
    assert first.concept_states[0].confidence == "high"

    second = _update(
        tracker,
        _analysis(
            missing=["backpropagation"],
            evidence=[],
            reasoning_quality="unclear",
        ),
        current_state=first,
    )

    backprop = second.concept_states[0]
    assert backprop.confidence == "high"
    assert backprop.demonstrated
    assert not backprop.missing
    assert backprop.evidence == ["Derived the gradient update step by step."]


def test_contradicting_evidence_lowers_confidence_without_discarding_it():
    """A later incorrect answer flags the concept but keeps the earlier demonstration."""
    tracker = KnowledgeStateTracker()

    first = _update(
        tracker,
        _analysis(
            demonstrated=["gradient_descent"],
            evidence=["Explained the learning-rate schedule correctly."],
        ),
    )
    second = _update(
        tracker,
        _analysis(
            incorrect=["gradient_descent"],
            evidence=["Claimed the learning rate sets the batch size."],
            reasoning_quality="weak",
        ),
        current_state=first,
    )

    concept = second.concept_states[0]
    assert concept.incorrect
    assert concept.demonstrated
    assert concept.confidence == "medium"
    assert len(concept.evidence) == 2


def test_missing_evidence_is_not_treated_as_lack_of_knowledge():
    """A turn with no concept evidence must leave the accumulated state untouched."""
    tracker = KnowledgeStateTracker()

    first = _update(
        tracker,
        _analysis(demonstrated=["indexing"], evidence=["Explained composite indexes."]),
    )
    second = _update(
        tracker,
        _analysis(evidence=[], reasoning_quality="unclear"),
        current_state=first,
    )

    assert [entry.concept for entry in second.concept_states] == ["indexing"]
    assert second.concept_states[0].confidence == "high"
    assert second.concept_states[0].evidence == ["Explained composite indexes."]


def test_single_turn_behaviour_is_unchanged_without_prior_state():
    """Without prior state the tracker still derives the state from the current answer alone."""
    tracker = KnowledgeStateTracker()

    state = _update(tracker, _analysis(evidence=["Answered in general terms."]))

    assert [entry.concept for entry in state.concept_states] == ["general_response"]
    assert state.claim_verifications == []


def test_claim_verification_accumulates_evidence_across_answers():
    """Repeated support for a claim should strengthen it and keep all evidence."""
    claim = Claim(
        claim_text="Improved model accuracy by 18%",
        category="quantitative",
        resume_evidence="Improved model accuracy by 18%.",
    )
    tracker = KnowledgeStateTracker()

    first = tracker.verify_resume_claim(
        claim,
        answer_analysis=_analysis(
            demonstrated=["model evaluation"],
            evidence=["Reported an 18% lift on the validation set."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Reported an 18% lift on the validation set.",
                }
            ],
        ),
    )
    assert first.status == "supported"

    second = tracker.verify_resume_claim(
        claim,
        answer_analysis=_analysis(
            demonstrated=["baseline comparison"],
            evidence=["Described the baseline the 18% was measured against."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Described the baseline the 18% was measured against.",
                }
            ],
        ),
        previous_verification=first,
    )

    assert second.status == "supported"
    assert second.confidence == "high"
    assert "Reported an 18% lift on the validation set." in second.evidence
    assert "Described the baseline the 18% was measured against." in second.evidence


def test_claim_verification_keeps_earlier_status_when_a_later_answer_is_uncertain():
    """An inconclusive later answer must not discard an established verification."""
    claim = Claim(
        claim_text="Improved model accuracy by 18%",
        category="quantitative",
        resume_evidence="Improved model accuracy by 18%.",
    )
    tracker = KnowledgeStateTracker()

    supported = tracker.verify_resume_claim(
        claim,
        answer_analysis=_analysis(
            demonstrated=["model evaluation"],
            evidence=["Reported an 18% lift on the validation set."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Reported an 18% lift on the validation set.",
                }
            ],
        ),
    )

    after_uncertain_turn = tracker.verify_resume_claim(
        claim,
        answer_analysis=_analysis(missing=["deployment details"], evidence=[]),
        previous_verification=supported,
    )
    assert after_uncertain_turn.status == "supported"
    assert "Reported an 18% lift on the validation set." in after_uncertain_turn.evidence

    contradicted = tracker.verify_resume_claim(
        claim,
        answer_analysis=_analysis(
            evidence=["Could not describe how the 18% was measured."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "contradicts",
                    "evidence": "Could not describe how the 18% was measured.",
                }
            ],
        ),
        previous_verification=after_uncertain_turn,
    )
    assert contradicted.status == "unsupported"
    assert contradicted.confidence == "medium"
    assert any("conflicts" in note for note in contradicted.notes)


def _claim(text: str = "Improved model accuracy by 18%") -> Claim:
    return Claim(
        claim_text=text,
        category="quantitative",
        context="Sentiment analysis project",
        resume_evidence=f"{text}.",
    )


def test_pending_resume_claim_is_verified_from_the_answer():
    """A claim the answer speaks to must be verified and recorded in the knowledge state."""
    tracker = KnowledgeStateTracker()

    state = _update(
        tracker,
        _analysis(
            demonstrated=["model evaluation"],
            evidence=["Reported an 18% lift on the validation set."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Reported an 18% lift on the validation set.",
                }
            ],
        ),
        resume_claims=[_claim()],
    )

    assert len(state.claim_verifications) == 1
    verification = state.claim_verifications[0]
    assert verification.claim_text == "Improved model accuracy by 18%"
    assert verification.status == "supported"
    assert "model evaluation" in {entry.concept for entry in state.concept_states}
    assert "Improved model accuracy by 18%" not in {
        entry.concept for entry in state.concept_states
    }


def test_claims_the_answer_does_not_address_are_not_verified():
    """An unmentioned claim must stay unverified rather than be judged on absent evidence."""
    tracker = KnowledgeStateTracker()

    state = _update(
        tracker,
        _analysis(demonstrated=["caching"], evidence=["Explained cache invalidation."]),
        resume_claims=[_claim(), _claim("Led a team of six engineers")],
    )

    assert state.claim_verifications == []


def test_claim_verification_accumulates_across_turns_through_the_state():
    """Claim evidence gathered over several turns must accumulate in the knowledge state."""
    tracker = KnowledgeStateTracker()
    claims = [_claim()]

    first = _update(
        tracker,
        _analysis(
            demonstrated=["model evaluation"],
            evidence=["Reported an 18% lift on the validation set."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Reported an 18% lift on the validation set.",
                }
            ],
        ),
        resume_claims=claims,
    )
    second = _update(
        tracker,
        _analysis(
            demonstrated=["baseline comparison"],
            evidence=["Described the baseline the 18% was measured against."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Described the baseline the 18% was measured against.",
                }
            ],
        ),
        current_state=first,
        resume_claims=claims,
    )

    assert len(second.claim_verifications) == 1
    verification = second.claim_verifications[0]
    assert verification.status == "supported"
    assert verification.confidence == "high"
    assert "Reported an 18% lift on the validation set." in verification.evidence
    assert "Described the baseline the 18% was measured against." in verification.evidence


def test_conflicting_claim_evidence_is_preserved_in_the_state():
    """Contradicting later evidence must be kept alongside the earlier supporting evidence."""
    tracker = KnowledgeStateTracker()
    claims = [_claim()]

    supported = _update(
        tracker,
        _analysis(
            demonstrated=["model evaluation"],
            evidence=["Reported an 18% lift on the validation set."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Reported an 18% lift on the validation set.",
                }
            ],
        ),
        resume_claims=claims,
    )
    conflicted = _update(
        tracker,
        _analysis(
            missing=["measurement methodology"],
            evidence=["Could not say how the 18% was measured."],
            reasoning_quality="weak",
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "contradicts",
                    "evidence": "Could not say how the 18% was measured.",
                }
            ],
        ),
        current_state=supported,
        resume_claims=claims,
    )

    verification = conflicted.claim_verifications[0]
    assert verification.status == "unsupported"
    assert "Reported an 18% lift on the validation set." in verification.evidence
    assert "Could not say how the 18% was measured." in verification.evidence
    assert any("conflicts" in note for note in verification.notes)


def test_concept_evidence_is_attributed_to_its_own_concept():
    """Per-concept evidence must not leak onto the other concepts of the same answer."""
    tracker = KnowledgeStateTracker()

    state = _update(
        tracker,
        _analysis(
            demonstrated=["attention"],
            missing=["tokenization"],
            incorrect=["positional_encoding"],
            evidence=["Whole-answer summary evidence."],
            concept_evidence=[
                {
                    "concept": "attention",
                    "evidence": ["Explained scaled dot-product attention."],
                },
                {
                    "concept": "tokenization",
                    "evidence": ["Never mentioned how text was tokenized."],
                },
                {
                    "concept": "positional_encoding",
                    "evidence": ["Said positional encodings are learned by attention."],
                },
            ],
        ),
    )

    concepts = {entry.concept: entry for entry in state.concept_states}
    assert concepts["attention"].evidence == ["Explained scaled dot-product attention."]
    assert concepts["tokenization"].evidence == ["Never mentioned how text was tokenized."]
    assert concepts["positional_encoding"].evidence == [
        "Said positional encodings are learned by attention."
    ]


def test_concept_without_its_own_evidence_records_none():
    """When per-concept evidence is supplied, unattributed concepts record no evidence."""
    tracker = KnowledgeStateTracker()

    state = _update(
        tracker,
        _analysis(
            demonstrated=["attention"],
            missing=["tokenization"],
            evidence=["Whole-answer summary evidence."],
            concept_evidence=[
                {
                    "concept": "attention",
                    "evidence": ["Explained scaled dot-product attention."],
                }
            ],
        ),
    )

    concepts = {entry.concept: entry for entry in state.concept_states}
    assert concepts["tokenization"].evidence == []
    assert concepts["tokenization"].missing
    assert not concepts["tokenization"].demonstrated
    assert not concepts["tokenization"].incorrect


def test_concept_evidence_accumulates_per_concept_across_turns():
    """Each concept keeps only its own evidence as turns accumulate."""
    tracker = KnowledgeStateTracker()

    first = _update(
        tracker,
        _analysis(
            demonstrated=["attention"],
            concept_evidence=[
                {"concept": "attention", "evidence": ["Explained the attention scores."]}
            ],
        ),
    )
    second = _update(
        tracker,
        _analysis(
            demonstrated=["attention", "tokenization"],
            concept_evidence=[
                {"concept": "attention", "evidence": ["Compared attention variants."]},
                {"concept": "tokenization", "evidence": ["Described byte-pair encoding."]},
            ],
        ),
        current_state=first,
    )

    concepts = {entry.concept: entry for entry in second.concept_states}
    assert concepts["attention"].evidence == [
        "Explained the attention scores.",
        "Compared attention variants.",
    ]
    assert concepts["tokenization"].evidence == ["Described byte-pair encoding."]


def test_only_well_evidenced_claims_count_as_sufficiently_verified():
    """Support with accumulated evidence resolves a claim; weaker or conflicting states do not."""
    tracker = KnowledgeStateTracker()
    claims = [_claim(), _claim("Led a team of six engineers")]

    thin_support = _update(
        tracker,
        _analysis(
            evidence=[],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": None,
                }
            ],
        ),
        resume_claims=claims,
    )
    assert thin_support.claim_verifications[0].confidence == "medium"
    assert tracker.sufficiently_verified_claims(thin_support) == []

    corroborated = _update(
        tracker,
        _analysis(
            evidence=["Walked through the measurement setup."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "supports",
                    "evidence": "Reported an 18% lift on the validation set.",
                }
            ],
        ),
        current_state=thin_support,
        resume_claims=claims,
    )
    assert tracker.sufficiently_verified_claims(corroborated) == [
        "Improved model accuracy by 18%"
    ]

    contradicted = _update(
        tracker,
        _analysis(
            evidence=["Could not say how the 18% was measured."],
            claim_relationships=[
                {
                    "claim_text": "Improved model accuracy by 18%",
                    "relationship": "contradicts",
                    "evidence": "Could not say how the 18% was measured.",
                }
            ],
        ),
        current_state=corroborated,
        resume_claims=claims,
    )
    assert tracker.sufficiently_verified_claims(contradicted) == []


def test_missing_concept_is_not_recorded_as_a_demonstrated_absence():
    """A missing concept must be marked under-evidenced, not incorrect or demonstrated."""
    tracker = KnowledgeStateTracker()

    state = _update(
        tracker,
        _analysis(
            missing=["sharding"],
            evidence=["The answer never covered sharding."],
            reasoning_quality="unclear",
        ),
    )

    sharding = state.concept_states[0]
    assert sharding.missing
    assert not sharding.demonstrated
    assert not sharding.incorrect
    assert sharding.confidence == "low"
