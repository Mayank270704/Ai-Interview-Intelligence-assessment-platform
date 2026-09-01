"""Interview conversation state tracking."""

from __future__ import annotations

from typing import Any


class InterviewConversationState:
    """Track the current state of the interview conversation."""

    def __init__(self, interview_id: str):
        """Initialize conversation state for an interview."""
        self.interview_id = interview_id
        self.conversation_turns: list[dict[str, Any]] = []
        self.current_topic: str = ""
        self.explored_concepts: set[str] = set()
        self._pending_claims: dict[str, str] = {}
        self.unresolved_gaps: list[str] = []
        self.question_count: int = 0

    def add_turn(
        self,
        question: str,
        answer: str,
        action: str | None = None,
        target_concept: str | None = None,
    ) -> None:
        """Record a question-answer exchange."""
        turn = {
            "question": question,
            "answer": answer,
            "action": action,
            "target_concept": target_concept,
            "turn_number": len(self.conversation_turns) + 1,
        }
        self.conversation_turns.append(turn)
        self.question_count += 1

    def mark_concept_explored(self, concept: str) -> None:
        """Mark a concept as sufficiently explored."""
        self.explored_concepts.add(concept.lower())

    @property
    def pending_claims(self) -> list[str]:
        """Human-readable text of the resume claims still pending verification."""
        return list(self._pending_claims.values())

    @property
    def pending_claim_ids(self) -> list[str]:
        """Stable identities of the resume claims still pending verification."""
        return list(self._pending_claims)

    def add_pending_claim(self, claim_id: str, claim_text: str) -> None:
        """Track a resume claim, identified by its stable id, as pending verification."""
        if claim_id and claim_id not in self._pending_claims:
            self._pending_claims[claim_id] = claim_text

    def resolve_pending_claim(self, claim_id: str) -> None:
        """Stop tracking a resume claim once its stable id has been resolved."""
        self._pending_claims.pop(claim_id, None)

    def pending_claim_id_for_text(self, claim_text: str) -> str | None:
        """Resolve claim text produced by the LLM back to the stable id it refers to."""
        target = claim_text.strip().lower()
        for claim_id, text in self._pending_claims.items():
            if text.strip().lower() == target:
                return claim_id
        return None

    def add_unresolved_gap(self, gap: str) -> None:
        """Record an unresolved knowledge gap."""
        if gap and gap not in self.unresolved_gaps:
            self.unresolved_gaps.append(gap)

    def resolve_gap(self, gap: str) -> None:
        """Mark a knowledge gap as resolved."""
        if gap in self.unresolved_gaps:
            self.unresolved_gaps.remove(gap)

    def get_recent_turns(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get the most recent interview turns."""
        return self.conversation_turns[-limit:] if self.conversation_turns else []

    def has_explored_concept(self, concept: str) -> bool:
        """Check if a concept has been sufficiently explored."""
        return concept.lower() in self.explored_concepts

    def is_concept_repeated(self, concept: str) -> bool:
        """Check if we have recently asked about this concept."""
        normalized = concept.lower()
        recent = self.get_recent_turns(5)
        for turn in recent:
            if (
                turn.get("target_concept")
                and normalized in turn["target_concept"].lower()
            ):
                return True
        return False

    def get_state_summary(self) -> dict[str, Any]:
        """Get a summary of the current interview state."""
        return {
            "interview_id": self.interview_id,
            "question_count": self.question_count,
            "current_topic": self.current_topic,
            "explored_concepts": list(self.explored_concepts),
            "pending_claims": self.pending_claims,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recent_turns": self.get_recent_turns(3),
        }
