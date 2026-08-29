"""Claim extraction from resume text."""

import re


def extract_potential_claims(text: str) -> list[dict[str, str]]:
    """
    Extract potential claims from resume text using regex patterns.

    Looks for quantitative and achievement claims that can be verified.
    The full claim extraction and validation is done by Gemini in the resume processor.

    Args:
        text: Resume text

    Returns:
        List of dictionaries with potential claims
    """
    claims = []

    # Pattern for quantitative claims (e.g., "increased by 20%", "improved from X to Y")
    quantitative_pattern = r"(?:improved|increased|decreased|reduced|boosted|enhanced|optimized)[\w\s]*(?:by|to)\s+(\d+%|[\d.]+x|\d+\s*\w+)"

    for match in re.finditer(quantitative_pattern, text, re.IGNORECASE):
        claim_context = text[max(0, match.start() - 50) : min(len(text), match.end() + 50)]
        claims.append(
            {"type": "quantitative", "claim": match.group(0), "context": claim_context}
        )

    # Pattern for achievement/technology claims
    achievement_pattern = r"(?:built|developed|created|implemented|designed|architected)[\w\s]*(?:a|an)?[\w\s]+(system|tool|platform|framework|application|service|solution)"

    for match in re.finditer(achievement_pattern, text, re.IGNORECASE):
        claim_context = text[max(0, match.start() - 50) : min(len(text), match.end() + 50)]
        claims.append(
            {"type": "technical", "claim": match.group(0), "context": claim_context}
        )

    return claims