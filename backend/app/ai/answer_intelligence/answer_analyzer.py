"""Answer analysis service for structured interview assessment."""

import json
from typing import Any

from app.ai.llm.client import LLMClient
from app.schemas.answer import AnswerAnalysis
from app.schemas.resume import CandidateProfile


class AnswerAnalyzer:
    """Analyze a candidate answer against a question and candidate profile."""

    def __init__(self):
        """Initialize the analyzer with the configured LLM client."""
        self.llm_client = LLMClient()

    @staticmethod
    def _build_candidate_summary(candidate_profile: CandidateProfile | None) -> str:
        """Create a concise, evidence-based summary from the candidate profile."""
        if candidate_profile is None:
            return "No candidate profile provided."

        identity = getattr(candidate_profile, "identity", None)
        parts: list[str] = []

        if identity and identity.full_name:
            parts.append(f"Candidate: {identity.full_name}")
        if identity and identity.location:
            parts.append(f"Location: {identity.location}")
        if candidate_profile.professional_summary:
            parts.append(f"Summary: {candidate_profile.professional_summary}")

        skills = [skill.name for skill in candidate_profile.skills[:10]]
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")

        technologies = [tech.name for tech in candidate_profile.technologies[:10]]
        if technologies:
            parts.append(f"Technologies: {', '.join(technologies)}")

        claims = [claim.claim_text for claim in candidate_profile.claims[:5]]
        if claims:
            parts.append(f"Resume claims: {', '.join(claims)}")

        return " | ".join(parts) if parts else "No candidate profile data available."

    @staticmethod
    def _build_analysis_prompt(
        question: str,
        answer: str,
        candidate_profile: CandidateProfile | None,
        interview_context: dict[str, Any] | None,
    ) -> str:
        """Build a structured prompt for the LLM answer analysis."""
        candidate_summary = AnswerAnalyzer._build_candidate_summary(candidate_profile)
        context_summary = json.dumps(interview_context or {}, ensure_ascii=False)

        return f"""Analyze the candidate's answer for an interview question.

Rules:
- Use only the supplied question, answer, candidate profile, and interview context.
- Do not invent or assume facts that are not present.
- Base your assessment on evidence in the answer and candidate profile.
- If the answer is vague, incomplete, or unsupported, say so explicitly.
- Keep the output strict JSON matching the AnswerAnalysis schema.

Question:
---
{question}
---

Candidate answer:
---
{answer}
---

Candidate profile summary:
---
{candidate_summary}
---

Interview context:
---
{context_summary}
---

Assess the answer for:
- technical correctness
- demonstrated concepts
- missing concepts
- incorrect concepts
- reasoning quality
- answer relevance to the question
- technical depth
- completeness
- unsupported or questionable claims
- relationship to relevant resume claims
- recommended next actions for a future interviewer
- evidence used to support the assessment
- evidence grouped per concept, listing for each demonstrated, missing, or incorrect concept only the evidence that relates to that concept

Recommended action values must be selected from this set:
probe_deeper, clarify, challenge, increase_difficulty, decrease_difficulty, change_topic, investigate_resume_claim, conclude_topic

Return valid JSON matching the AnswerAnalysis schema.
"""

    def analyze_answer(
        self,
        question: str,
        answer: str,
        candidate_profile: CandidateProfile | None = None,
        interview_context: dict[str, Any] | None = None,
    ) -> AnswerAnalysis:
        """Analyze a candidate answer and return a structured assessment."""
        prompt = self._build_analysis_prompt(
            question=question,
            answer=answer,
            candidate_profile=candidate_profile,
            interview_context=interview_context,
        )

        try:
            return self.llm_client.generate_structured(prompt, AnswerAnalysis)
        except Exception as exc:
            raise ValueError(f"Failed to analyze answer: {exc}") from exc
