"""Resume section extraction."""

import re


def extract_resume_sections(text: str) -> dict[str, str]:
    """
    Extract major sections from resume text.

    Uses common section headers to identify resume sections.

    Args:
        text: Cleaned resume text

    Returns:
        Dictionary mapping section names to their content
    """
    sections = {}

    # Common section headers
    section_patterns = {
        "contact": r"(?:Contact|Phone|Email)",
        "summary": r"(?:Professional Summary|Summary|Objective|Profile)",
        "education": r"(?:Education|Degree|University|School)",
        "experience": r"(?:Experience|Work Experience|Employment)",
        "skills": r"(?:Skills|Technical Skills|Competencies)",
        "projects": r"(?:Projects|Portfolio)",
        "certifications": r"(?:Certifications|Certificates|Licenses)",
        "achievements": r"(?:Achievements|Awards|Honors)",
    }

    text_lower = text.lower()

    for section_name, pattern in section_patterns.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            start_pos = match.start()
            # Find the next section header
            remaining_text = text_lower[match.end() :]
            next_match = None
            for other_section, other_pattern in section_patterns.items():
                if other_section != section_name:
                    m = re.search(other_pattern, remaining_text, re.IGNORECASE)
                    if m:
                        if next_match is None or m.start() < next_match.start():
                            next_match = m

            end_pos = (
                match.end() + next_match.start() if next_match else len(text)
            )
            sections[section_name] = text[start_pos:end_pos].strip()

    return sections