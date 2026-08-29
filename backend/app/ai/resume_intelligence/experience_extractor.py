"""Work experience extraction from resume text."""

import re


def extract_experience_entries(text: str) -> list[dict[str, str]]:
    """
    Extract work experience entries from resume text using regex patterns.

    This is a simple heuristic extractor. The full extraction and
    validation is done by Gemini in the resume processor.

    Args:
        text: Resume text

    Returns:
        List of dictionaries with company, position, and dates
    """
    experiences = []

    # Pattern for company name and position
    # Matches patterns like: "Company Name | Position" or "Position at Company Name"
    pattern = r"(?:(?P<company>.*?)\s*\|\s*(?P<position>.*?))|(?P<position2>.*?)\s+at\s+(?P<company2>.*?)(?:\n|$)"

    for match in re.finditer(pattern, text, re.MULTILINE):
        company = match.group("company") or match.group("company2")
        position = match.group("position") or match.group("position2")

        if company and position:
            # Try to find dates near this entry
            date_pattern = r"(?:(?P<start_month>\w+)\s*(?P<start_year>\d{4}))?\s*[-–]\s*(?:(?P<end_month>\w+)\s*(?P<end_year>\d{4})|(?P<current>Present|Current))"
            date_match = re.search(date_pattern, text)

            experiences.append(
                {
                    "company": company.strip(),
                    "position": position.strip(),
                    "dates": date_match.group(0) if date_match else None,
                }
            )

    return experiences