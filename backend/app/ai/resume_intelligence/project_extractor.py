"""Project extraction from resume text."""

import re


def extract_projects(text: str) -> list[dict[str, str]]:
    """
    Extract project entries from resume text using regex patterns.

    This is a simple heuristic extractor. The full extraction and
    validation is done by Gemini in the resume processor.

    Args:
        text: Resume text

    Returns:
        List of dictionaries with project information
    """
    projects = []

    # Pattern for project entries (basic heuristic)
    # Looks for patterns like "Project Name:" or "• Project Name"
    project_pattern = r"(?:(?:Project|Project Name)[\s:]+|•\s*)([^\n]+)"

    for match in re.finditer(project_pattern, text, re.IGNORECASE):
        project_name = match.group(1).strip()
        if project_name and len(project_name) > 3:
            projects.append({"name": project_name})

    return projects