"""Structured, deterministic ATS diagnostics.

Every diagnostic here is derived only from the already-extracted CandidateProfile
(the same structured data the numeric scorer reads) plus, where the LLM captured
one, a `resume_evidence` quote. No diagnostic changes or feeds back into the
numeric ats_score -- this module is a read-only second pass over already-computed
scores/feedback and the profile itself.

What is NOT implemented here, and why (documented rather than faked):

- Spelling/typo signals: detecting a genuine misspelling reliably requires a
  dictionary/lexicon (or an LLM). Adding one would mean either a new dependency
  or an LLM call, both explicitly out of scope for this deterministic, LLM-free
  feature. A naive regex heuristic would produce arbitrary false positives on
  proper nouns, technology names, and abbreviations, which would violate "do not
  invent issues" more than it would help. Left unsupported.

- Non-standard/malformed section HEADINGS: the original heading text (its exact
  wording, casing, or formatting as it appeared in the PDF) is never retained.
  ResumeProcessor extracts a plain text string from the PDF (pdf_processor.py),
  and only the LLM's *structured* CandidateProfile output is ever persisted --
  the raw/cleaned PDF text itself is discarded after the LLM call and never
  stored. There is no heading text left to inspect by the time ATS scoring runs
  against a persisted resume. Left unsupported (this is distinct from "missing
  standard sections", which checks structured-field presence and *is*
  supported below).

- Full layout/formatting analysis (columns, fonts, tables, true bullet-list
  detection): pypdf's page.extract_text() returns a flat text stream with no
  positional/layout metadata, and that flat text isn't persisted either. Only a
  narrow, evidence-grounded proxy is feasible (see `_broken_bullet_diagnostics`
  below, which flags literal bullet glyphs glued together inside a single
  extracted text field) -- not genuine layout analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.resume import CandidateProfile

_REPLACEMENT_CHAR = "�"
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BULLET_CHARS = "•‣●▪◦∙"
_MAX_EVIDENCE_LENGTH = 160

_DATE_FORMATS: list[tuple[str, re.Pattern[str]]] = [
    ("present", re.compile(r"^present$", re.IGNORECASE)),
    ("year", re.compile(r"^\d{4}$")),
    ("month year", re.compile(r"^[A-Za-z]{3,9}\.?\s+\d{4}$")),
    ("MM/YYYY", re.compile(r"^\d{1,2}/\d{4}$")),
    ("YYYY-MM", re.compile(r"^\d{4}-\d{1,2}$")),
]


@dataclass
class Diagnostic:
    type: str
    section: str
    affected_text: str | None
    explanation: str
    actionable_fix: str


def _truncate(text: str, limit: int = _MAX_EVIDENCE_LENGTH) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _classify_date_format(value: str) -> str | None:
    """Return a recognized date-format label for a date string, or None if unrecognized.

    Unrecognized formats are excluded from the consistency comparison rather than
    treated as a mismatch, since a format we can't classify isn't reliable evidence
    of inconsistency either way.
    """
    cleaned = value.strip()
    for label, pattern in _DATE_FORMATS:
        if pattern.match(cleaned):
            return label
    return None


def _date_consistency_diagnostic(
    section: str, entries: list[tuple[str | None, str | None]]
) -> Diagnostic | None:
    values = [v for pair in entries for v in pair if v]
    classified = [(v, _classify_date_format(v)) for v in values]
    recognized = [(v, fmt) for v, fmt in classified if fmt and fmt != "present"]
    distinct_formats = sorted({fmt for _, fmt in recognized})
    if len(distinct_formats) <= 1:
        return None

    examples = ", ".join(f"'{v}'" for v, _ in recognized[:4])
    return Diagnostic(
        type="date_format_inconsistency",
        section=section,
        affected_text=examples,
        explanation=(
            f"The {section} section mixes different date formats "
            f"({', '.join(distinct_formats)}), which can confuse ATS parsers "
            "that expect one consistent format."
        ),
        actionable_fix=f"Use one consistent date format (e.g. 'Jan 2020') across every {section} entry.",
    )


def _date_diagnostics(profile: CandidateProfile) -> list[Diagnostic]:
    diagnostics = []
    experience_dates = [(e.start_date, e.end_date) for e in profile.experience]
    education_dates = [(e.start_date, e.end_date) for e in profile.education]

    for section, dates in (("experience", experience_dates), ("education", education_dates)):
        diagnostic = _date_consistency_diagnostic(section, dates)
        if diagnostic:
            diagnostics.append(diagnostic)
    return diagnostics


def _find_duplicates(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    originals: dict[str, str] = {}
    for value in values:
        key = value.strip().lower()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
        originals.setdefault(key, value.strip())
    return [originals[key] for key, count in counts.items() if count > 1]


def _duplicate_diagnostics(profile: CandidateProfile) -> list[Diagnostic]:
    diagnostics = []

    skill_names = [s.name for s in profile.skills] + [t.name for t in profile.technologies]
    dupes = _find_duplicates(skill_names)
    if dupes:
        diagnostics.append(Diagnostic(
            type="duplicate_content",
            section="skills",
            affected_text=", ".join(dupes[:5]),
            explanation="The same skill or technology is listed more than once.",
            actionable_fix="Remove the duplicate skill/technology entries.",
        ))

    # Includes start_date so a candidate who genuinely left and rejoined the same
    # company in the same role (a common, legitimate pattern) isn't flagged as a
    # duplicate -- only an exact repeat with the same start date is.
    experience_keys = [f"{e.company} - {e.position} - {e.start_date or ''}" for e in profile.experience]
    dupes = _find_duplicates(experience_keys)
    if dupes:
        diagnostics.append(Diagnostic(
            type="duplicate_content",
            section="experience",
            affected_text=", ".join(dupes[:5]),
            explanation="The same company, position, and start date appears more than once in work experience.",
            actionable_fix="Merge or remove the duplicate experience entries.",
        ))

    # Includes date for the same reason -- e.g. a recurring annual project/event.
    project_keys = [f"{p.name} - {p.date or ''}" for p in profile.projects]
    dupes = _find_duplicates(project_keys)
    if dupes:
        diagnostics.append(Diagnostic(
            type="duplicate_content",
            section="projects",
            affected_text=", ".join(dupes[:5]),
            explanation="The same project name and date appears more than once.",
            actionable_fix="Merge or rename the duplicate project entries.",
        ))

    dupes = _find_duplicates([c.claim_text for c in profile.claims])
    if dupes:
        diagnostics.append(Diagnostic(
            type="duplicate_content",
            section="achievements",
            affected_text=", ".join(dupes[:3]),
            explanation="The same achievement/claim text appears more than once.",
            actionable_fix="Remove the duplicate achievement entries.",
        ))

    return diagnostics


def _text_fields(profile: CandidateProfile) -> list[tuple[str, str, str]]:
    """Every free-text field the ATS engine actually has access to: (section, label, text)."""
    fields: list[tuple[str, str, str]] = []
    if profile.professional_summary:
        fields.append(("summary", "professional summary", profile.professional_summary))
    if profile.identity.resume_evidence:
        fields.append(("contact", "identity evidence", profile.identity.resume_evidence))
    for e in profile.experience:
        if e.description:
            fields.append(("experience", f"'{e.position or e.company}' description", e.description))
        if e.resume_evidence:
            fields.append(("experience", f"'{e.position or e.company}' evidence", e.resume_evidence))
    for p in profile.projects:
        if p.description:
            fields.append(("projects", f"'{p.name}' description", p.description))
        if p.resume_evidence:
            fields.append(("projects", f"'{p.name}' evidence", p.resume_evidence))
    for a in profile.achievements:
        if a.description:
            fields.append(("achievements", f"'{a.title}' description", a.description))
    for c in profile.claims:
        fields.append(("achievements", "claim evidence", c.resume_evidence))
    return fields


def _unusual_character_diagnostics(profile: CandidateProfile) -> list[Diagnostic]:
    diagnostics = []
    for section, label, text in _text_fields(profile):
        if _REPLACEMENT_CHAR in text:
            diagnostics.append(Diagnostic(
                type="unusual_characters",
                section=section,
                affected_text=_truncate(text),
                explanation=(
                    f"The {label} contains a Unicode replacement character, typically a sign "
                    "that the original PDF's text did not extract cleanly (e.g. an embedded "
                    "font or symbol pypdf could not decode)."
                ),
                actionable_fix="Re-export the resume as a standard text-based PDF and re-upload it.",
            ))
        if _CONTROL_CHAR_PATTERN.search(text):
            diagnostics.append(Diagnostic(
                type="unusual_characters",
                section=section,
                affected_text=_truncate(text),
                explanation=f"The {label} contains non-printable control characters, which can confuse ATS parsers.",
                actionable_fix="Re-save the resume from its original source document rather than a converted copy.",
            ))
    return diagnostics


def _broken_bullet_diagnostics(profile: CandidateProfile) -> list[Diagnostic]:
    diagnostics = []
    for section, label, text in _text_fields(profile):
        bullet_count = sum(text.count(ch) for ch in _BULLET_CHARS)
        if bullet_count >= 2:
            diagnostics.append(Diagnostic(
                type="broken_bullet_or_extraction_signal",
                section=section,
                affected_text=_truncate(text),
                explanation=(
                    f"The {label} contains multiple bullet characters within one block of text. "
                    "This commonly happens when a PDF's bullet list items are extracted without "
                    "line breaks between them."
                ),
                actionable_fix=(
                    "Confirm this section renders as a proper bulleted list in the original "
                    "document, and consider exporting from a simpler single-column layout."
                ),
            ))
    return diagnostics


def _contact_info_diagnostic(profile: CandidateProfile) -> Diagnostic | None:
    missing = []
    if not profile.identity.email:
        missing.append("email")
    if not profile.identity.phone:
        missing.append("phone number")
    if not missing:
        return None
    return Diagnostic(
        type="missing_contact_info",
        section="contact",
        affected_text=None,
        explanation=f"The resume is missing: {', '.join(missing)}.",
        actionable_fix="Add complete contact information (email and phone number) near the top of the resume.",
    )


def _experience_structure_diagnostics(profile: CandidateProfile) -> list[Diagnostic]:
    if not profile.experience:
        return []  # absence of experience is already surfaced via missing_standard_section

    diagnostics = []
    for entry in profile.experience:
        missing = []
        if not entry.company:
            missing.append("company")
        if not entry.position:
            missing.append("position")
        if not entry.start_date:
            missing.append("start date")
        if not entry.description or not entry.description.strip():
            missing.append("description")
        if missing:
            diagnostics.append(Diagnostic(
                type="unclear_experience_structure",
                section="experience",
                affected_text=entry.position or entry.company or None,
                explanation=f"This experience entry is missing: {', '.join(missing)}.",
                actionable_fix="Include company, position, start date, and a description of responsibilities/impact.",
            ))
    return diagnostics


def _project_structure_diagnostics(profile: CandidateProfile) -> list[Diagnostic]:
    if not profile.projects:
        return []  # absence of projects is already surfaced via missing_standard_section

    diagnostics = []
    for entry in profile.projects:
        missing = []
        if not entry.description or not entry.description.strip():
            missing.append("description")
        if not entry.technologies:
            missing.append("technologies used")
        if missing:
            diagnostics.append(Diagnostic(
                type="unclear_project_structure",
                section="projects",
                affected_text=entry.name,
                explanation=f"The project '{entry.name}' is missing: {', '.join(missing)}.",
                actionable_fix="Add a description and list the technologies used for every project.",
            ))
    return diagnostics


def _measurable_impact_diagnostic(profile: CandidateProfile) -> Diagnostic | None:
    count = sum(1 for c in profile.claims if c.category == "quantitative")
    if count > 0:
        return None
    return Diagnostic(
        type="lack_of_measurable_impact",
        section="achievements",
        affected_text=None,
        explanation="No measurable, quantified achievements (e.g. percentages, metrics, counts) were found.",
        actionable_fix="Add specific numbers to demonstrate impact, e.g. 'improved performance by 20%' or 'led a team of 5'.",
    )


def _missing_section_diagnostics(section_feedback: list[str]) -> list[Diagnostic]:
    """Reuses the scorer's own section-completeness feedback rather than recomputing it."""
    diagnostics = []
    for item in section_feedback:
        if not item.startswith("Missing or empty"):
            continue
        name = item.removeprefix("Missing or empty ").removesuffix(" section.")
        diagnostics.append(Diagnostic(
            type="missing_standard_section",
            section=name,
            affected_text=None,
            explanation=item,
            actionable_fix=f"Add a clearly labeled {name} section to the resume.",
        ))
    return diagnostics


def _jd_keyword_diagnostics(missing_keywords: list[str], missing_skills: list[str]) -> list[Diagnostic]:
    diagnostics = []
    if missing_keywords:
        diagnostics.append(Diagnostic(
            type="missing_jd_keywords",
            section="job_description",
            affected_text=", ".join(missing_keywords[:10]),
            explanation="These job description terms were not found anywhere in the resume.",
            actionable_fix="If genuinely applicable, incorporate these terms naturally into skills, experience, or project descriptions.",
        ))
    if missing_skills:
        diagnostics.append(Diagnostic(
            type="missing_jd_skills",
            section="job_description",
            affected_text=", ".join(missing_skills[:10]),
            explanation="These job description terms were not found among the resume's formally listed skills/technologies.",
            actionable_fix="If you have relevant experience with these, add them explicitly to your skills or technologies list.",
        ))
    return diagnostics


def build_diagnostics(
    profile: CandidateProfile,
    section_feedback: list[str],
    missing_keywords: list[str] | None = None,
    missing_skills: list[str] | None = None,
) -> list[Diagnostic]:
    """Assemble every supported diagnostic for a resume.

    Purely a read pass over the profile and the scorer's already-computed
    section_feedback/missing_keywords/missing_skills -- nothing here is fed back
    into the numeric ats_score.
    """
    diagnostics: list[Diagnostic] = []

    contact = _contact_info_diagnostic(profile)
    if contact:
        diagnostics.append(contact)

    diagnostics.extend(_missing_section_diagnostics(section_feedback))
    diagnostics.extend(_date_diagnostics(profile))
    diagnostics.extend(_duplicate_diagnostics(profile))
    diagnostics.extend(_experience_structure_diagnostics(profile))
    diagnostics.extend(_project_structure_diagnostics(profile))
    diagnostics.extend(_unusual_character_diagnostics(profile))
    diagnostics.extend(_broken_bullet_diagnostics(profile))

    impact = _measurable_impact_diagnostic(profile)
    if impact:
        diagnostics.append(impact)

    if missing_keywords or missing_skills:
        diagnostics.extend(_jd_keyword_diagnostics(missing_keywords or [], missing_skills or []))

    return diagnostics
