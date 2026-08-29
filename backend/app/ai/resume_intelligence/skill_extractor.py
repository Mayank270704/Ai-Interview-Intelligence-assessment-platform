"""Skill extraction from resume text."""

import re


def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract potential skills from resume text using regex patterns.

    This is a simple heuristic extractor. The full skill extraction and
    validation is done by Gemini in the resume processor.

    Args:
        text: Resume text

    Returns:
        List of potential skill phrases
    """
    skills = []

    # Pattern for skills listed after "Skills:" or "Technical Skills:"
    skill_section_match = re.search(
        r"(?:Skills|Technical Skills|Competencies)[\s:]*\n(.*?)(?:\n\n|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if skill_section_match:
        skills_text = skill_section_match.group(1)
        # Split by common delimiters
        for skill in re.split(r"[,;•\n-]", skills_text):
            skill_clean = skill.strip()
            if skill_clean and len(skill_clean) > 2:
                skills.append(skill_clean)

    return list(set(skills))  # Remove duplicates