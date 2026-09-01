"""Candidate knowledge state tracking and resume claim verification."""

from __future__ import annotations

from app.schemas.answer import AnswerAnalysis
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.knowledge_state import CandidateKnowledgeState, ClaimVerification, ConceptState
from app.schemas.resume import Claim

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


class KnowledgeStateTracker:
    """Track evidence-based concept confidence and verify resume claims without making interview decisions."""

    @staticmethod
    def _concept_confidence_from_analysis(answer_analysis: AnswerAnalysis) -> str:
        if answer_analysis.incorrect_concepts:
            return "low"
        if answer_analysis.demonstrated_concepts:
            return "high" if answer_analysis.reasoning_quality in {"strong", "adequate"} else "medium"
        if answer_analysis.missing_concepts and not answer_analysis.evidence:
            return "low"
        return "medium"

    @staticmethod
    def _evidence_for_concept(concept: str, answer_analysis: AnswerAnalysis) -> list[str]:
        """Return the evidence attributed to one concept, falling back to answer-level evidence."""
        if not answer_analysis.concept_evidence:
            return list(answer_analysis.evidence)

        key = concept.strip().lower()
        matched: list[str] = []
        for entry in answer_analysis.concept_evidence:
            if entry.concept.strip().lower() == key:
                matched.extend(item for item in entry.evidence if item.strip())
        return list(dict.fromkeys(matched))

    @classmethod
    def _evaluate_concept_status(cls, concept: str, answer_analysis: AnswerAnalysis) -> ConceptState:
        evidence = cls._evidence_for_concept(concept, answer_analysis)
        demonstrated = concept.lower() in {item.lower() for item in answer_analysis.demonstrated_concepts}
        missing = concept.lower() in {item.lower() for item in answer_analysis.missing_concepts}
        incorrect = concept.lower() in {item.lower() for item in answer_analysis.incorrect_concepts}

        if incorrect:
            confidence = "low"
        elif demonstrated:
            confidence = "high" if answer_analysis.reasoning_quality in {"strong", "adequate"} else "medium"
        elif missing:
            confidence = "low"
        else:
            confidence = "medium"

        return ConceptState(
            concept=concept,
            confidence=confidence,
            demonstrated=demonstrated,
            missing=missing,
            incorrect=incorrect,
            evidence=evidence,
        )

    @staticmethod
    def _higher_confidence(first: str, second: str) -> str:
        return first if _CONFIDENCE_RANK[first] >= _CONFIDENCE_RANK[second] else second

    @classmethod
    def _merge_concept_state(cls, previous: ConceptState, current: ConceptState) -> ConceptState:
        """Combine an accumulated concept state with the evidence from the latest answer."""
        evidence = list(dict.fromkeys([*previous.evidence, *current.evidence]))
        demonstrated = previous.demonstrated or current.demonstrated
        incorrect = current.incorrect or (previous.incorrect and not current.demonstrated)
        missing = False if demonstrated else (previous.missing or current.missing)

        if incorrect:
            confidence = "medium" if demonstrated else "low"
        elif current.demonstrated and previous.demonstrated:
            confidence = "high"
        elif current.demonstrated:
            confidence = cls._higher_confidence(previous.confidence, current.confidence)
        elif demonstrated:
            confidence = previous.confidence
        else:
            confidence = cls._higher_confidence(previous.confidence, current.confidence)

        return ConceptState(
            concept=previous.concept,
            confidence=confidence,
            demonstrated=demonstrated,
            missing=missing,
            incorrect=incorrect,
            evidence=evidence,
        )

    @classmethod
    def _accumulate_concept_states(
        cls,
        accumulated: list[ConceptState],
        turn_states: list[ConceptState],
    ) -> list[ConceptState]:
        """Merge the latest turn into the accumulated states, keeping untouched concepts intact."""
        merged = [entry.model_copy(deep=True) for entry in accumulated]
        positions = {entry.concept.lower(): index for index, entry in enumerate(merged)}

        for turn_state in turn_states:
            key = turn_state.concept.lower()
            index = positions.get(key)
            if index is None:
                merged.append(turn_state)
                positions[key] = len(merged) - 1
            else:
                merged[index] = cls._merge_concept_state(merged[index], turn_state)

        return merged

    @staticmethod
    def _build_summary(concept_states: list[ConceptState]) -> str:
        summary_parts: list[str] = []
        strong = [entry.concept for entry in concept_states if entry.confidence == "high"]
        weak = [entry.concept for entry in concept_states if entry.confidence == "low"]
        if strong:
            summary_parts.append(f"Strong evidence for: {', '.join(strong[:3])}.")
        if weak:
            summary_parts.append(f"Needs follow-up: {', '.join(weak[:3])}.")
        return " ".join(summary_parts) if summary_parts else "No concrete concept evidence was recorded yet."

    @staticmethod
    def _claims_referenced_by_answer(
        resume_claims: list[Claim],
        answer_analysis: AnswerAnalysis,
    ) -> list[Claim]:
        """Select the resume claims the current answer actually says something about."""
        referenced = {
            item.claim_text.strip().lower()
            for item in answer_analysis.resume_claim_relationships
        }
        referenced.update(
            claim_text.strip().lower() for claim_text in answer_analysis.unsupported_claims
        )
        return [
            claim
            for claim in resume_claims
            if claim.claim_text.strip().lower() in referenced
        ]

    def _accumulate_claim_verifications(
        self,
        resume_claims: list[Claim],
        answer_analysis: AnswerAnalysis,
        accumulated: list[ClaimVerification],
    ) -> list[ClaimVerification]:
        """Verify the claims this answer touches and merge them into earlier verifications."""
        verifications = [entry.model_copy(deep=True) for entry in accumulated]
        positions = {
            entry.identity: index for index, entry in enumerate(verifications)
        }

        for claim in self._claims_referenced_by_answer(resume_claims, answer_analysis):
            key = claim.identity
            index = positions.get(key)
            verification = self.verify_resume_claim(
                claim,
                answer_analysis=answer_analysis,
                previous_verification=verifications[index] if index is not None else None,
            )
            if index is None:
                verifications.append(verification)
                positions[key] = len(verifications) - 1
            else:
                verifications[index] = verification

        return verifications

    @staticmethod
    def sufficiently_verified_claim_ids(state: CandidateKnowledgeState) -> list[str]:
        """Stable ids of the claims whose accumulated evidence resolves them."""
        return [
            verification.identity
            for verification in state.claim_verifications
            if verification.status == "supported" and verification.confidence == "high"
        ]

    def update_from_answer(
        self,
        question: str,
        answer: str,
        answer_analysis: AnswerAnalysis,
        answer_evaluation: AnswerEvaluation | None = None,
        current_state: CandidateKnowledgeState | None = None,
        resume_claims: list[Claim] | None = None,
    ) -> CandidateKnowledgeState:
        """Merge the evidence from this answer into the knowledge state accumulated so far."""
        concepts: list[str] = []
        concepts.extend(answer_analysis.demonstrated_concepts)
        concepts.extend(answer_analysis.missing_concepts)
        concepts.extend(answer_analysis.incorrect_concepts)

        deduplicated = []
        seen: set[str] = set()
        for concept in concepts:
            normalized = concept.strip()
            key = normalized.lower()
            if normalized and key not in seen:
                deduplicated.append(normalized)
                seen.add(key)

        turn_states = [self._evaluate_concept_status(concept, answer_analysis) for concept in deduplicated]
        accumulated = list(current_state.concept_states) if current_state else []

        if not turn_states and not accumulated:
            turn_states = [
                ConceptState(
                    concept="general_response",
                    confidence=self._concept_confidence_from_analysis(answer_analysis),
                    demonstrated=bool(answer_analysis.demonstrated_concepts),
                    missing=bool(answer_analysis.missing_concepts),
                    incorrect=bool(answer_analysis.incorrect_concepts),
                    evidence=list(answer_analysis.evidence),
                )
            ]

        concept_states = self._accumulate_concept_states(accumulated, turn_states)
        claim_verifications = self._accumulate_claim_verifications(
            resume_claims or [],
            answer_analysis,
            current_state.claim_verifications if current_state else [],
        )

        return CandidateKnowledgeState(
            concept_states=concept_states,
            claim_verifications=claim_verifications,
            summary=self._build_summary(concept_states),
        )

    @classmethod
    def _merge_claim_verification(
        cls,
        previous: ClaimVerification,
        current: ClaimVerification,
    ) -> ClaimVerification:
        """Combine an earlier claim verification with the evidence from the latest answer."""
        evidence = list(dict.fromkeys([*previous.evidence, *current.evidence]))
        notes = list(dict.fromkeys([*previous.notes, *current.notes]))

        if current.status == previous.status:
            status = current.status
            confidence = cls._higher_confidence(previous.confidence, current.confidence)
            if status != "uncertain" and len(evidence) >= 2:
                confidence = "high"
        elif current.status == "uncertain":
            status = previous.status
            confidence = previous.confidence
        elif previous.status == "uncertain":
            status = current.status
            confidence = current.confidence
        else:
            status = current.status
            confidence = "medium"
            notes.append(
                "Earlier interview evidence conflicts with the latest answer for this claim."
            )

        return ClaimVerification(
            claim_id=previous.claim_id or current.claim_id,
            claim_text=previous.claim_text,
            status=status,
            confidence=confidence,
            evidence=evidence,
            notes=notes,
        )

    def verify_resume_claim(
        self,
        claim: Claim,
        answer_analysis: AnswerAnalysis,
        previous_verification: ClaimVerification | None = None,
    ) -> ClaimVerification:
        """Verify a resume claim, accumulating evidence from any earlier verification."""
        related = answer_analysis.resume_claim_relationships
        matching = [item for item in related if item.claim_text.lower() == claim.claim_text.lower()]
        support = any(item.relationship == "supports" for item in matching)
        contradiction = any(item.relationship == "contradicts" for item in matching)
        evidence = [item.evidence for item in matching if item.evidence]
        evidence.extend(answer_analysis.evidence)
        evidence = list(dict.fromkeys(evidence))

        if contradiction:
            status = "unsupported"
            confidence = "high"
        elif support and not answer_analysis.incorrect_concepts:
            status = "supported"
            confidence = "high" if len(evidence) >= 2 else "medium"
        elif answer_analysis.unsupported_claims and claim.claim_text in answer_analysis.unsupported_claims:
            status = "unsupported"
            confidence = "medium"
        elif answer_analysis.incorrect_concepts or answer_analysis.missing_concepts:
            status = "uncertain"
            confidence = "medium" if evidence else "low"
        else:
            status = "uncertain"
            confidence = "low"

        notes = []
        if status == "supported":
            notes.append("The answer directly supports the resume claim with evidence.")
        elif status == "unsupported":
            notes.append("The answer does not provide credible support for the resume claim.")
        else:
            notes.append("The claim remains uncertain because the current evidence is incomplete.")

        verification = ClaimVerification(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=status,
            confidence=confidence,
            evidence=evidence,
            notes=notes,
        )

        if previous_verification is None:
            return verification

        return self._merge_claim_verification(previous_verification, verification)
