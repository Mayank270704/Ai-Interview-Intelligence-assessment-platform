"""Deterministic ATS resume scoring.

Two modes, both scored as the mean of five independent 0-100 signals so no single
signal can dominate and the formula stays easy to audit:

Mode "readiness" (no job description) -- how complete and ATS-parseable the resume
itself is, independent of any job:
  section_completeness, skills_presence, experience_structure, project_structure,
  measurable_impact

Mode "jd_match" (job description supplied) -- how well the resume's own content
overlaps with the job description's significant terms:
  section_completeness, keyword_match, experience_relevance, project_relevance,
  measurable_impact

No LLM call is made anywhere in this module -- every score and every piece of
feedback is computed from the already-extracted CandidateProfile with plain,
reproducible arithmetic and text matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.ats.diagnostics import Diagnostic, build_diagnostics
from app.ai.ats.keywords import (
    contains_term,
    extract_jd_terms,
    resume_corpus,
    resume_skill_vocabulary,
)
from app.schemas.resume import CandidateProfile

_QUANTITATIVE_CLAIM_CATEGORY = "quantitative"
_MAX_JD_TEXT_LENGTH = 20_000


class InvalidJobDescriptionError(ValueError):
    """Raised when a supplied job description fails validation."""


@dataclass
class ATSScoreResult:
    ats_score: int
    mode: str
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    section_feedback: list[str] = field(default_factory=list)
    experience_feedback: list[str] = field(default_factory=list)
    project_feedback: list[str] = field(default_factory=list)
    measurable_impact_feedback: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _section_completeness(profile: CandidateProfile) -> tuple[int, list[str]]:
    sections = {
        "professional summary": bool(profile.professional_summary and profile.professional_summary.strip()),
        "skills": bool(profile.skills or profile.technologies),
        "experience": bool(profile.experience),
        "education": bool(profile.education),
        "projects": bool(profile.projects),
        "achievements or certifications": bool(profile.achievements or profile.certifications),
        "contact details": bool(profile.identity.email or profile.identity.phone),
    }
    present = [name for name, ok in sections.items() if ok]
    missing = [name for name, ok in sections.items() if not ok]

    feedback = [f"{name.capitalize()} section present." for name in present]
    feedback.extend(f"Missing or empty {name} section." for name in missing)

    score = _clamp(100 * len(present) / len(sections))
    return score, feedback


def _skills_presence(profile: CandidateProfile) -> int:
    count = len(profile.skills) + len(profile.technologies)
    return _clamp(100 * min(count, 8) / 8)


def _experience_structure(profile: CandidateProfile) -> tuple[int, list[str]]:
    if not profile.experience:
        return 0, ["No work experience entries were found in the resume."]

    complete = 0
    feedback: list[str] = []
    for entry in profile.experience:
        fields_present = [
            bool(entry.company),
            bool(entry.position),
            bool(entry.start_date),
            bool(entry.description and entry.description.strip()),
        ]
        if all(fields_present):
            complete += 1
        elif not entry.description or not entry.description.strip():
            feedback.append(f"'{entry.position or entry.company}' has no description of responsibilities or impact.")

    score = _clamp(100 * complete / len(profile.experience))
    if not feedback:
        feedback.append("Experience entries are well-structured with dates and descriptions.")
    return score, feedback


def _experience_relevance(profile: CandidateProfile, jd_terms: list[str]) -> tuple[int, list[str]]:
    if not profile.experience:
        return 0, ["No work experience entries were found to match against the job description."]
    if not jd_terms:
        return 100, ["No job description terms available to compare against experience."]

    text = " ".join(
        f"{entry.position} {entry.description or ''}" for entry in profile.experience
    ).lower()
    matched = [term for term in jd_terms if contains_term(text, term)]
    score = _clamp(100 * len(matched) / len(jd_terms))

    feedback = (
        [f"Experience descriptions reference {len(matched)} of {len(jd_terms)} key job description terms."]
        if matched
        else ["Experience descriptions do not reference the job description's key terms."]
    )
    return score, feedback


def _project_structure(profile: CandidateProfile) -> tuple[int, list[str]]:
    if not profile.projects:
        return 0, ["No projects were found in the resume."]

    complete = 0
    for project in profile.projects:
        if project.description and project.technologies:
            complete += 1

    score = _clamp(100 * complete / len(profile.projects))
    feedback = (
        ["Projects include descriptions and technologies used."]
        if complete == len(profile.projects)
        else ["Some projects are missing a description or listed technologies."]
    )
    return score, feedback


def _project_relevance(profile: CandidateProfile, jd_terms: list[str]) -> tuple[int, list[str]]:
    if not profile.projects:
        return 0, ["No projects were found to match against the job description."]
    if not jd_terms:
        return 100, ["No job description terms available to compare against projects."]

    text = " ".join(
        f"{p.name} {p.description or ''} {' '.join(p.technologies or [])}" for p in profile.projects
    ).lower()
    matched = [term for term in jd_terms if contains_term(text, term)]
    score = _clamp(100 * len(matched) / len(jd_terms))

    feedback = (
        [f"Projects reference {len(matched)} of {len(jd_terms)} key job description terms."]
        if matched
        else ["Projects do not reference the job description's key terms."]
    )
    return score, feedback


def _measurable_impact(profile: CandidateProfile) -> tuple[int, list[str]]:
    quantitative_claims = [c for c in profile.claims if c.category == _QUANTITATIVE_CLAIM_CATEGORY]
    count = len(quantitative_claims)
    score = _clamp(100 * min(count, 3) / 3)

    if count == 0:
        feedback = [
            "No measurable, quantified achievements (e.g. percentages, metrics) were found. "
            "Consider adding specific numbers to demonstrate impact."
        ]
    else:
        feedback = [f"Found {count} measurable/quantified achievement(s) in the resume."]
    return score, feedback


def _in_skill_vocabulary(term: str, skill_vocabulary: set[str]) -> bool:
    """Whether a single JD term is covered by any (possibly multi-word) skill name."""
    return any(term == skill or term in skill.split() for skill in skill_vocabulary)


def _keyword_match(
    corpus: str, skill_vocabulary: set[str], jd_terms: list[str]
) -> tuple[int, list[str], list[str], list[str], list[str]]:
    if not jd_terms:
        return 100, [], [], [], []

    matched_keywords = [term for term in jd_terms if contains_term(corpus, term)]
    missing_keywords = [term for term in jd_terms if term not in matched_keywords]
    matched_skills = [term for term in jd_terms if _in_skill_vocabulary(term, skill_vocabulary)]
    missing_skills = [term for term in jd_terms if not _in_skill_vocabulary(term, skill_vocabulary)]

    score = _clamp(100 * len(matched_keywords) / len(jd_terms))
    return score, matched_keywords, missing_keywords, matched_skills, missing_skills


def _suggestions(
    section_feedback: list[str],
    experience_feedback: list[str],
    project_feedback: list[str],
    impact_feedback: list[str],
    missing_keywords: list[str],
) -> list[str]:
    suggestions: list[str] = []
    if any(item.startswith("Missing") for item in section_feedback):
        suggestions.append("Add the missing resume sections noted above to improve completeness.")
    if any("no description" in item.lower() or "no work experience" in item.lower() for item in experience_feedback):
        suggestions.append("Add clear descriptions of responsibilities and outcomes to each experience entry.")
    if any("no projects" in item.lower() or "missing a description" in item.lower() for item in project_feedback):
        suggestions.append("Add project descriptions and the technologies used for each project.")
    if any(item.startswith("No measurable") for item in impact_feedback):
        suggestions.append("Quantify achievements with specific numbers, percentages, or metrics where possible.")
    if missing_keywords:
        shown = ", ".join(missing_keywords[:8])
        suggestions.append(f"Consider addressing these job description terms if genuinely applicable: {shown}.")
    if not suggestions:
        suggestions.append("The resume is well-structured; no major gaps were identified.")
    return suggestions


def validate_job_description(job_description: str | None) -> str | None:
    """Normalize and validate a supplied job description, or return None for no-JD mode."""
    if job_description is None:
        return None
    cleaned = job_description.strip()
    if not cleaned:
        return None
    if len(cleaned) > _MAX_JD_TEXT_LENGTH:
        raise InvalidJobDescriptionError(
            f"Job description exceeds the maximum length of {_MAX_JD_TEXT_LENGTH} characters."
        )
    return cleaned


def score_resume(profile: CandidateProfile, job_description: str | None) -> ATSScoreResult:
    """Score a resume deterministically, in JD-compatibility mode or readiness mode."""
    cleaned_jd = validate_job_description(job_description)

    section_score, section_feedback = _section_completeness(profile)
    impact_score, impact_feedback = _measurable_impact(profile)

    if cleaned_jd is None:
        skills_score = _skills_presence(profile)
        experience_score, experience_feedback = _experience_structure(profile)
        project_score, project_feedback = _project_structure(profile)

        overall = _clamp(
            (section_score + skills_score + experience_score + project_score + impact_score) / 5
        )
        suggestions = _suggestions(section_feedback, experience_feedback, project_feedback, impact_feedback, [])
        diagnostics = build_diagnostics(profile, section_feedback)

        return ATSScoreResult(
            ats_score=overall,
            mode="readiness",
            section_feedback=section_feedback,
            experience_feedback=experience_feedback,
            project_feedback=project_feedback,
            measurable_impact_feedback=impact_feedback,
            suggestions=suggestions,
            diagnostics=diagnostics,
        )

    corpus = resume_corpus(profile)
    skill_vocabulary = resume_skill_vocabulary(profile)
    jd_terms = extract_jd_terms(cleaned_jd, extra_phrases=skill_vocabulary)

    keyword_score, matched_keywords, missing_keywords, matched_skills, missing_skills = _keyword_match(
        corpus, skill_vocabulary, jd_terms
    )
    experience_score, experience_feedback = _experience_relevance(profile, jd_terms)
    project_score, project_feedback = _project_relevance(profile, jd_terms)

    overall = _clamp(
        (section_score + keyword_score + experience_score + project_score + impact_score) / 5
    )
    suggestions = _suggestions(
        section_feedback, experience_feedback, project_feedback, impact_feedback, missing_keywords
    )
    diagnostics = build_diagnostics(profile, section_feedback, missing_keywords, missing_skills)

    return ATSScoreResult(
        ats_score=overall,
        mode="jd_match",
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        section_feedback=section_feedback,
        experience_feedback=experience_feedback,
        project_feedback=project_feedback,
        measurable_impact_feedback=impact_feedback,
        suggestions=suggestions,
        diagnostics=diagnostics,
    )
