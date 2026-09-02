"""Deterministic text/keyword utilities for ATS resume scoring.

Keyword extraction is phrase-aware: a curated set of common multi-word technical
phrases (plus the resume's own multi-word skill/technology names, supplied by the
caller) is matched against the job description text first and removed from it, so
"machine learning" is captured as one term instead of splitting into the two
generic-looking tokens "machine" and "learning". Whatever text remains is then
tokenized word-by-word as before. No LLM and no NLP dependency is used anywhere
in this module -- matching is plain, deterministic substring/regex text matching.
"""

from __future__ import annotations

import re
from collections import Counter

from app.schemas.resume import CandidateProfile

_TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}")

_STOPWORDS = {
    # Function words
    "the", "and", "or", "a", "an", "to", "of", "in", "on", "for", "with", "as",
    "is", "are", "was", "were", "be", "been", "being", "this", "that", "these",
    "those", "it", "its", "at", "by", "from", "into", "about", "we", "you",
    "your", "our", "will", "must", "have", "has", "had", "can", "may", "should",
    "not", "but", "if", "than", "then", "so", "such", "who", "which", "what",
    "all", "any", "other", "more", "most", "some", "each", "per", "etc",
    "across", "within", "including", "include", "up", "out", "also", "well",
    "when", "where", "while", "there", "here", "how", "why", "both",
    # Generic recruiting / job-posting boilerplate
    "role", "job", "jobs", "work", "working", "works", "team", "teams",
    "company", "companies", "opportunity", "opportunities", "candidate",
    "candidates", "applicant", "applicants", "apply", "application", "hire",
    "hiring", "hired", "join", "joining", "employer", "employment",
    "experience", "years", "year", "required", "requirements", "requirement",
    "preferred", "responsibilities", "responsibility", "qualifications",
    "qualification", "skills", "skill", "ability", "abilities", "strong",
    "excellent", "good", "great", "new", "environment", "position",
    "positions", "looking", "seek", "seeking", "ideal", "plus", "big",
    "must-have", "nice-to-have", "location", "locations", "remote", "onsite",
    "hybrid", "salary", "benefits", "compensation", "full-time", "part-time",
    "fulltime", "parttime", "contract",
    # Generic responsibility verbs (too generic to discriminate one job from another)
    "build", "building", "builds", "built", "deploy", "deploying", "deployed",
    "deploys", "drive", "driving", "drives", "driven", "ensure", "ensuring",
    "ensures", "provide", "providing", "provides", "provided", "deliver",
    "delivering", "delivers", "delivered", "develop", "developing", "develops",
    "developed", "grow", "growing", "grows", "help", "helping", "helps",
    "support", "supporting", "supports", "supported", "maintain",
    "maintaining", "maintains", "manage", "managing", "manages", "managed",
    "collaborate", "collaborating", "collaborates", "create", "creating",
    "creates", "created", "leverage", "leveraging", "leverages", "utilize",
    "utilizing", "utilizes", "perform", "performing", "performs",
    "implement", "implementing", "implements", "implemented", "participate",
    "participating", "contribute", "contributing", "contributes",
    "demonstrate", "demonstrating", "demonstrated", "identify", "identifying",
    "using", "use", "used", "uses",
    # Generic filler adjectives/nouns
    "dynamic", "innovative", "passionate", "fast-paced", "fastpaced",
    "motivated", "detail-oriented", "self-starter", "hands-on", "handson",
    "platforms", "platform", "solutions", "solution", "products", "product",
    "capability", "capabilities", "level", "levels", "areas", "area",
    "aspects", "aspect", "various", "multiple", "wide", "range", "related",
    "relevant", "similar", "diverse", "overall", "typically", "generally",
    # Short filler/function words admitted now that the minimum token length is 2
    "no", "now", "us", "yet", "yes", "did", "do", "does", "let", "get", "got",
    "own", "off", "far", "fit", "via", "amid", "upon", "among",
    # Logistics/eligibility boilerplate common in job postings
    "visa", "sponsorship", "relocation", "eligible", "eligibility",
    "authorized", "authorization", "citizen", "citizenship", "available",
    "availability", "need", "needs", "needed", "someone", "everyone",
}

_MIN_TOKEN_LENGTH = 2
_MAX_JD_TERMS = 30

# A curated set of common multi-word technical/domain phrases so genuinely
# meaningful concepts survive extraction as single terms instead of being
# split into separate, individually-generic-looking words.
_KNOWN_PHRASES = {
    # ML / AI / data
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "artificial intelligence", "reinforcement learning",
    "neural network", "neural networks", "data science", "data engineering",
    "data analysis", "data pipeline", "data pipelines", "feature engineering",
    "model training", "model deployment", "large language model",
    "large language models", "generative ai", "recommendation system",
    "recommendation systems", "time series", "computer science",
    # Infrastructure / cloud / systems
    "cloud computing", "continuous integration", "continuous deployment",
    "continuous delivery", "ci/cd", "infrastructure as code",
    "version control", "object oriented", "object-oriented",
    "test driven development", "test-driven development", "distributed systems",
    "microservices architecture", "system design", "load balancing",
    "database design", "rest api", "restful api", "message queue",
    "message queues", "high availability", "fault tolerance",
    # Engineering practices / roles
    "agile methodology", "agile methodologies", "software development",
    "software engineering", "project management", "product management",
    "code review", "code reviews", "unit testing", "integration testing",
    "problem solving", "cross functional", "cross-functional",
    "full stack", "full-stack", "front end", "front-end", "back end",
    "back-end", "version control system", "api design",
}

_PHRASE_PATTERNS = {
    phrase: re.compile(rf"\b{re.escape(phrase)}\b") for phrase in _KNOWN_PHRASES
}


def tokenize(text: str) -> list[str]:
    """Extract lowercase word-like tokens from free text, dropping stopwords/noise."""
    tokens = [
        match.group(0).lower().strip(".,;:") for match in _TOKEN_PATTERN.finditer(text or "")
    ]
    return [
        token
        for token in tokens
        if len(token) >= _MIN_TOKEN_LENGTH and token not in _STOPWORDS
    ]


def _extract_phrase_counts(text: str, extra_phrases: frozenset[str]) -> tuple[dict[str, int], str]:
    """Find known multi-word phrases in text, returning their counts and the remaining text."""
    remaining = text
    counts: dict[str, int] = {}
    all_phrases = sorted(_KNOWN_PHRASES | extra_phrases, key=len, reverse=True)
    for phrase in all_phrases:
        if " " not in phrase and "-" not in phrase and "/" not in phrase:
            continue  # single-word "phrases" are handled by the normal tokenizer
        pattern = _PHRASE_PATTERNS.get(phrase) or re.compile(rf"\b{re.escape(phrase)}\b")
        matches = pattern.findall(remaining)
        if matches:
            counts[phrase] = len(matches)
            remaining = pattern.sub(" ", remaining)
    return counts, remaining


def extract_jd_terms(
    job_description: str,
    extra_phrases: frozenset[str] | set[str] = frozenset(),
    limit: int = _MAX_JD_TERMS,
) -> list[str]:
    """Extract the most significant terms from a job description, by frequency.

    Deterministic and phrase-aware: known multi-word technical phrases (plus any
    extra_phrases supplied, e.g. the resume's own skill names) are matched and
    removed first, then the remaining text is tokenized word-by-word after dropping
    stopwords and generic job-posting boilerplate. Terms are ordered by frequency
    (ties broken alphabetically) so the same job description always yields the same
    term list regardless of when or how many times it is scored.
    """
    text = (job_description or "").lower()
    phrase_counts, remaining_text = _extract_phrase_counts(text, frozenset(extra_phrases))
    token_counts = Counter(tokenize(remaining_text))

    combined: dict[str, int] = dict(token_counts)
    combined.update(phrase_counts)

    ordered = sorted(combined.items(), key=lambda item: (-item[1], item[0]))
    return [term for term, _ in ordered[:limit]]


def resume_corpus(profile: CandidateProfile) -> str:
    """Concatenate the resume's extracted text into one lowercase searchable corpus."""
    parts: list[str] = []
    if profile.professional_summary:
        parts.append(profile.professional_summary)
    parts.extend(skill.name for skill in profile.skills)
    parts.extend(tech.name for tech in profile.technologies)
    parts.extend(profile.languages)
    for experience in profile.experience:
        parts.append(experience.position)
        if experience.description:
            parts.append(experience.description)
    for project in profile.projects:
        parts.append(project.name)
        if project.description:
            parts.append(project.description)
        if project.technologies:
            parts.extend(project.technologies)
    for claim in profile.claims:
        parts.append(claim.claim_text)
    return " ".join(parts).lower()


def resume_skill_vocabulary(profile: CandidateProfile) -> set[str]:
    """The resume's own formally listed skill and technology names, lowercased."""
    return {skill.name.lower() for skill in profile.skills} | {
        tech.name.lower() for tech in profile.technologies
    }


def contains_term(corpus: str, term: str) -> bool:
    """Whether a term appears in a text corpus, as a whole word/token where possible.

    Uses alphanumeric lookaround rather than \\b, because \\b requires a word/non-word
    *transition* and so never matches at the edge of a term that itself ends or starts
    with a symbol (e.g. "c#", "c++") when that edge is followed/preceded by another
    non-word character such as whitespace -- \\b would silently never match those terms.
    """
    if " " in term or "-" in term or "/" in term:
        return term in corpus
    pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    return re.search(pattern, corpus) is not None
