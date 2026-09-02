"""Tests for deterministic ATS keyword/text utilities."""

import pytest

from app.ai.ats.keywords import (
    contains_term,
    extract_jd_terms,
    resume_corpus,
    resume_skill_vocabulary,
    tokenize,
)
from app.schemas.resume import CandidateIdentity, CandidateProfile, Experience, Project, Skill, Technology


def test_tokenize_lowercases_and_strips_trailing_punctuation():
    tokens = tokenize("Docker, Kubernetes. AWS!")

    assert "docker" in tokens
    assert "kubernetes" in tokens


def test_tokenize_drops_stopwords_and_short_tokens():
    tokens = tokenize("We are looking for a strong candidate with experience.")

    assert tokens == []


def test_extract_jd_terms_is_frequency_ordered_and_deterministic():
    jd = "Python Python Python SQL SQL Docker"

    terms = extract_jd_terms(jd)

    assert terms[0] == "python"
    assert terms[1] == "sql"
    assert "docker" in terms


def test_extract_jd_terms_is_reproducible_across_calls():
    jd = "Python engineer with Kubernetes and Docker experience required."

    assert extract_jd_terms(jd) == extract_jd_terms(jd)


def test_extract_jd_terms_respects_limit():
    jd = " ".join(f"word{i}" for i in range(50))

    terms = extract_jd_terms(jd, limit=5)

    assert len(terms) == 5


def _profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe"),
        skills=[Skill(name="Machine Learning"), Skill(name="Python")],
        technologies=[Technology(name="PyTorch")],
        experience=[Experience(company="Acme", position="ML Engineer", description="Built systems.")],
        projects=[Project(name="Recsys", description="A recommender.", technologies=["Docker"])],
    )


def test_resume_corpus_includes_skills_experience_and_projects():
    corpus = resume_corpus(_profile())

    assert "machine learning" in corpus
    assert "ml engineer" in corpus
    assert "recsys" in corpus
    assert "docker" in corpus


def test_resume_skill_vocabulary_contains_only_skills_and_technologies():
    vocabulary = resume_skill_vocabulary(_profile())

    assert vocabulary == {"machine learning", "python", "pytorch"}


def test_contains_term_matches_multi_word_terms_as_substrings():
    assert contains_term("experienced machine learning engineer", "machine learning")


def test_contains_term_matches_single_word_terms_at_word_boundaries():
    assert contains_term("java developer", "java")
    assert not contains_term("javascript developer", "java")


def test_generic_hiring_boilerplate_is_excluded_from_jd_terms():
    jd = (
        "We are hiring a passionate, hands-on engineer to join our growing team. "
        "This is a great opportunity to build and deploy platforms. Strong "
        "communication skills are a plus. Looking for a big-picture thinker."
    )

    terms = extract_jd_terms(jd)

    for generic in (
        "hiring", "hands-on", "join", "growing", "opportunity", "build",
        "deploy", "platforms", "plus", "looking", "big",
    ):
        assert generic not in terms, f"expected '{generic}' to be filtered as boilerplate"


def test_meaningful_technical_terms_survive_extraction():
    jd = "Looking for an engineer with Python, Kubernetes, and PostgreSQL experience."

    terms = extract_jd_terms(jd)

    assert "python" in terms
    assert "kubernetes" in terms
    assert "postgresql" in terms


@pytest.mark.parametrize(
    "phrase",
    [
        "machine learning",
        "natural language processing",
        "system design",
        "deep learning",
        "computer vision",
        "continuous integration",
        "distributed systems",
        "software engineering",
    ],
)
def test_known_multi_word_technical_phrases_are_preserved_as_single_terms(phrase):
    jd = f"We need someone with strong {phrase} experience for this role."

    terms = extract_jd_terms(jd)

    assert phrase in terms
    for word in phrase.split():
        assert word not in terms, f"'{word}' should be absorbed into the phrase '{phrase}', not left standalone"


def test_multi_word_phrase_extraction_does_not_double_count_component_words():
    jd = "Strong background in machine learning and natural language processing required."

    terms = extract_jd_terms(jd)

    assert "machine learning" in terms
    assert "natural language processing" in terms
    assert "machine" not in terms
    assert "learning" not in terms
    assert "natural" not in terms
    assert "language" not in terms
    assert "processing" not in terms


def test_resume_specific_multi_word_skills_are_recognized_via_extra_phrases():
    jd = "Looking for someone with experience in behavioral driven development."

    without_extra = extract_jd_terms(jd)
    with_extra = extract_jd_terms(jd, extra_phrases={"behavioral driven development"})

    assert "behavioral driven development" not in without_extra
    assert "behavioral driven development" in with_extra


def test_extraction_is_case_insensitive():
    jd = "MACHINE LEARNING and Python and KUBERNETES are required."

    terms = extract_jd_terms(jd)

    assert "machine learning" in terms
    assert "python" in terms
    assert "kubernetes" in terms


def test_extraction_remains_deterministic_with_phrases():
    jd = "Machine learning, natural language processing, and Python experience required."

    assert extract_jd_terms(jd) == extract_jd_terms(jd)


def test_contains_term_matches_terms_ending_in_symbols():
    """Regression: word-boundary matching requires a word/non-word transition, so it silently never
    matched terms like "c#"/"c++" when followed by whitespace. Verified via
    lookaround instead."""
    assert contains_term("experienced in c# development", "c#")
    assert contains_term("experienced in c++ development", "c++")
    assert contains_term("proficient in c#.", "c#")


def test_short_technical_terms_are_recovered_not_dropped():
    """Regression: the minimum token length previously excluded legitimate
    2-character tech terms entirely."""
    terms = extract_jd_terms("Looking for a Go developer with AI, ML, and C# experience.")

    assert "go" in terms
    assert "ai" in terms
    assert "ml" in terms
    assert "c#" in terms


def test_short_token_minimum_does_not_admit_generic_filler_words():
    """Regression: lowering the minimum token length to recover short tech terms
    must not also admit generic 2-3 letter filler words as if they were keywords."""
    jd = (
        "No visa sponsorship available. This is a great opportunity, so apply "
        "now if you are a good fit for our team in the US."
    )

    terms = extract_jd_terms(jd)

    for generic in ("no", "now", "us", "fit", "visa", "sponsorship", "available"):
        assert generic not in terms, f"expected '{generic}' to be filtered as boilerplate"
