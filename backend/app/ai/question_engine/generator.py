"""Question generation from an interview decision."""

from __future__ import annotations

from typing import Any

from app.ai.llm.client import LLMClient
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_decision import InterviewDecision
from app.schemas.knowledge import RetrievedKnowledge
from app.schemas.knowledge_state import CandidateKnowledgeState
from app.schemas.question import GeneratedQuestion, QuestionDifficulty
from app.schemas.resume import CandidateProfile


class QuestionGenerator:
    """Convert an InterviewDecision into a natural-language interview question."""

    def __init__(self):
        """Initialize the question generator with the configured LLM client."""
        self.llm_client = LLMClient()

    @staticmethod
    def _resolve_target_concept(decision: InterviewDecision) -> str:
        """Read the concept the decision points at, without re-deciding it."""
        if (
            decision.action in {"CHANGE_TOPIC", "EXPLORE_RELATED_CONCEPT"}
            and decision.next_topic
        ):
            return decision.next_topic.strip()
        return decision.target_concept.strip()

    @staticmethod
    def _build_candidate_context(candidate_profile: CandidateProfile | None) -> str:
        """Summarize only the resume facts available for grounding the question."""
        if candidate_profile is None:
            return "No candidate profile available."

        parts: list[str] = []

        if candidate_profile.professional_summary:
            parts.append(
                f"Professional summary: {candidate_profile.professional_summary}"
            )

        skills = [skill.name for skill in candidate_profile.skills[:10]]
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")

        technologies = [tech.name for tech in candidate_profile.technologies[:10]]
        if technologies:
            parts.append(f"Technologies: {', '.join(technologies)}")

        for project in candidate_profile.projects[:5]:
            details = [f"Project: {project.name}"]
            if project.role:
                details.append(f"role: {project.role}")
            if project.technologies:
                details.append(f"technologies: {', '.join(project.technologies)}")
            if project.description:
                details.append(f"description: {project.description}")
            parts.append(" | ".join(details))

        for experience in candidate_profile.experience[:5]:
            details = [f"Experience: {experience.position} at {experience.company}"]
            if experience.description:
                details.append(f"description: {experience.description}")
            parts.append(" | ".join(details))

        for claim in candidate_profile.claims[:8]:
            details = [
                f"Resume claim: {claim.claim_text}",
                f"category: {claim.category}",
            ]
            if claim.context:
                details.append(f"context: {claim.context}")
            details.append(f"resume evidence: {claim.resume_evidence}")
            parts.append(" | ".join(details))

        return "\n".join(parts) if parts else "No candidate profile data available."

    @staticmethod
    def _build_evaluation_context(answer_evaluation: AnswerEvaluation | None) -> str:
        """Summarize the evaluation evidence the question should build on."""
        if answer_evaluation is None:
            return "No evaluation of a previous answer is available."

        gaps = answer_evaluation.gaps[:5]
        strengths = answer_evaluation.strengths[:5]
        unsupported = answer_evaluation.unsupported_claims[:5]

        return "\n".join(
            [
                f"Technical correctness: {answer_evaluation.technical_correctness}",
                f"Conceptual understanding: {answer_evaluation.conceptual_understanding}",
                f"Completeness: {answer_evaluation.completeness}",
                f"Technical depth: {answer_evaluation.technical_depth}",
                f"Assessment confidence: {answer_evaluation.confidence}",
                f"Gaps: {', '.join(gaps) if gaps else 'None recorded'}",
                f"Strengths: {', '.join(strengths) if strengths else 'None recorded'}",
                f"Unsupported claims: {', '.join(unsupported) if unsupported else 'None recorded'}",
            ]
        )

    @staticmethod
    def _build_knowledge_state_context(
        knowledge_state: CandidateKnowledgeState | None,
    ) -> str:
        """Summarize the current knowledge estimate for the candidate."""
        if knowledge_state is None or not knowledge_state.concept_states:
            return "No concept-level knowledge evidence has been recorded yet."

        lines = [
            f"{entry.concept}: confidence={entry.confidence}, demonstrated={entry.demonstrated}, "
            f"missing={entry.missing}, incorrect={entry.incorrect}"
            for entry in knowledge_state.concept_states[:10]
        ]
        if knowledge_state.summary:
            lines.append(f"Summary: {knowledge_state.summary}")
        return "\n".join(lines)

    @staticmethod
    def _build_conversation_context(recent_turns: list[dict[str, Any]] | None) -> str:
        """Summarize the recent conversation so the question follows on naturally."""
        if not recent_turns:
            return "No previous conversation turns."

        lines: list[str] = []
        for turn in recent_turns[-3:]:
            lines.append(f"Q: {turn.get('question', '')}")
            lines.append(f"A: {turn.get('answer', '')}")
        return "\n".join(lines)

    @staticmethod
    def _build_retrieved_knowledge_context(
        retrieved_knowledge: list[RetrievedKnowledge] | None,
    ) -> str:
        """Format knowledge supplied by the caller; retrieval never happens here."""
        if not retrieved_knowledge:
            return "No retrieved knowledge was supplied."

        return "\n".join(
            f"[{item.source}] {item.title}: {item.content[:500]}"
            for item in retrieved_knowledge[:5]
        )

    @classmethod
    def _build_prompt(
        cls,
        decision: InterviewDecision,
        target_concept: str,
        difficulty: QuestionDifficulty,
        candidate_profile: CandidateProfile | None,
        answer_evaluation: AnswerEvaluation | None,
        knowledge_state: CandidateKnowledgeState | None,
        recent_turns: list[dict[str, Any]] | None,
        explored_concepts: list[str] | None,
        retrieved_knowledge: list[RetrievedKnowledge] | None,
    ) -> str:
        """Build the prompt that turns the decision into a single interview question."""
        explored = ", ".join(explored_concepts[:15]) if explored_concepts else "None"
        evidence = decision.reasoning_evidence[:5]
        evidence_summary = "; ".join(evidence) if evidence else "None recorded"
        claim = decision.resume_claim_to_investigate or "None specified"

        return f"""You are an expert technical interviewer conducting a live interview.

A separate reasoning system has already decided what should happen next. Your only job is to
phrase ONE interview question that carries out that decision naturally.

=== DECISION TO EXPRESS ===
Action: {decision.action}
Target concept: {target_concept}
Reasoning behind the action: {decision.reasoning}
Supporting evidence: {evidence_summary}
Resume claim to investigate: {claim}
Required difficulty: {difficulty}

=== WHAT EACH ACTION MEANS ===
DEEPEN: Probe the mechanism, implementation detail, trade-off, edge case, or deeper reasoning.
CLARIFY: Resolve an ambiguity or request the specific missing detail.
CHALLENGE: Professionally challenge an incorrect or unsupported statement and investigate the reasoning behind it.
INCREASE_DIFFICULTY: Move toward a more complex application, trade-off, architecture, or scenario.
DECREASE_DIFFICULTY: Move toward a more fundamental aspect of the concept to establish a foundation.
INVESTIGATE_CLAIM: Investigate the specific resume claim using the candidate's own resume evidence.
EXPLORE_RELATED_CONCEPT: Move to a related or prerequisite concept.
CHANGE_TOPIC: Transition naturally to the new competency or concept.
CONCLUDE_TOPIC: Close out the topic with a final consolidating question.

=== CANDIDATE CONTEXT (resume) ===
{cls._build_candidate_context(candidate_profile)}

=== RECENT CONVERSATION ===
{cls._build_conversation_context(recent_turns)}

=== EVALUATION EVIDENCE ===
{cls._build_evaluation_context(answer_evaluation)}

=== KNOWLEDGE STATE ===
{cls._build_knowledge_state_context(knowledge_state)}

=== RETRIEVED KNOWLEDGE CONTEXT ===
{cls._build_retrieved_knowledge_context(retrieved_knowledge)}

=== ALREADY EXPLORED CONCEPTS ===
{explored}

=== RULES ===
- Ask exactly one question, phrased the way a human interviewer would speak it.
- The question must carry out the decided action on the target concept.
- Match the required difficulty: {difficulty}.
- Ground the question only in information present in the context above.
- Never invent candidate experience, projects, skills, technologies, or claims.
- If you reference the candidate's work, reference only what the resume context actually states.
- Do not re-ask what the recent conversation already answered, and do not revisit an already
  explored concept unless the decision explicitly targets it.
- Do not include an answer, hints, commentary, or several stacked questions.
- Remain professional and respectful, especially when challenging the candidate.
- evaluation_focus must list the concepts or evidence the candidate's answer should be judged on,
  derived from the context above.

Return valid JSON matching the GeneratedQuestion schema.
"""

    def generate_question(
        self,
        decision: InterviewDecision,
        difficulty: QuestionDifficulty = "medium",
        candidate_profile: CandidateProfile | None = None,
        answer_evaluation: AnswerEvaluation | None = None,
        knowledge_state: CandidateKnowledgeState | None = None,
        recent_turns: list[dict[str, Any]] | None = None,
        explored_concepts: list[str] | None = None,
        retrieved_knowledge: list[RetrievedKnowledge] | None = None,
    ) -> GeneratedQuestion:
        """Generate the interview question that expresses the given decision."""
        target_concept = self._resolve_target_concept(decision)
        if not target_concept:
            raise ValueError(
                "Cannot generate a question: the decision has no target concept."
            )

        if decision.action == "INVESTIGATE_CLAIM" and not (
            decision.resume_claim_to_investigate
            or (candidate_profile and candidate_profile.claims)
        ):
            raise ValueError(
                "Cannot generate a claim investigation question: no resume claim is available."
            )

        prompt = self._build_prompt(
            decision=decision,
            target_concept=target_concept,
            difficulty=difficulty,
            candidate_profile=candidate_profile,
            answer_evaluation=answer_evaluation,
            knowledge_state=knowledge_state,
            recent_turns=recent_turns,
            explored_concepts=explored_concepts,
            retrieved_knowledge=retrieved_knowledge,
        )

        try:
            generated = self.llm_client.generate_structured(prompt, GeneratedQuestion)
        except Exception as exc:
            raise ValueError(f"Failed to generate question: {exc}") from exc

        if not generated.question.strip():
            raise ValueError("Generated question is empty.")

        return generated.model_copy(
            update={
                "question": generated.question.strip(),
                "target_concept": target_concept,
                "difficulty": difficulty,
                "intent": decision.action,
            }
        )
