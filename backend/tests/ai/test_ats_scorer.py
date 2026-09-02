"""Tests for deterministic ATS resume scoring."""

import pytest

from app.ai.ats.scorer import InvalidJobDescriptionError, score_resume
from app.schemas.resume import (
    CandidateIdentity,
    CandidateProfile,
    Certification,
    Education,
    Experience,
    Project,
    Claim,
    Skill,
    Technology,
)

JD_ML_ROLE = """
We are hiring a Machine Learning Engineer with strong Python skills and hands-on
experience with PyTorch, Docker, and Kubernetes. Experience with TensorFlow and
cloud platforms such as AWS is a plus. You will build and deploy production
recommendation systems.
"""


def _empty_profile() -> CandidateProfile:
    return CandidateProfile(identity=CandidateIdentity(full_name="Jane Doe"))


def _strong_profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe", email="jane@example.com", phone="555-0100"),
        professional_summary="Machine Learning Engineer with 5 years of production experience in Python.",
        education=[Education(institution="Stanford", degree="M.S.", field_of_study="CS")],
        skills=[Skill(name="Machine Learning"), Skill(name="Python")],
        technologies=[Technology(name="PyTorch"), Technology(name="Docker"), Technology(name="Kubernetes")],
        experience=[
            Experience(
                company="Acme",
                position="Machine Learning Engineer",
                start_date="2020",
                end_date="Present",
                description="Built and deployed production recommendation systems in Python using "
                "PyTorch, Docker, and Kubernetes, improving latency by 30%.",
            )
        ],
        projects=[
            Project(
                name="Recsys",
                description="Built a production recommendation system in Python using PyTorch and "
                "Docker for a machine learning pipeline.",
                technologies=["PyTorch", "Docker"],
            )
        ],
        certifications=[Certification(name="AWS Certified Machine Learning")],
        claims=[
            Claim(
                claim_text="Improved latency by 30%",
                category="quantitative",
                resume_evidence="improving latency by 30%",
            ),
            Claim(
                claim_text="Reduced training time by 40%",
                category="quantitative",
                resume_evidence="reduced training time by 40%",
            ),
        ],
    )


def _weak_profile() -> CandidateProfile:
    return CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe"),
        skills=[Skill(name="Communication")],
    )


# 1. Resume with no job description
def test_no_job_description_returns_readiness_mode():
    result = score_resume(_strong_profile(), None)

    assert result.mode == "readiness"
    assert result.matched_keywords == []
    assert result.missing_keywords == []


def test_blank_job_description_is_treated_as_no_job_description():
    result = score_resume(_strong_profile(), "   ")

    assert result.mode == "readiness"


# 2 / 3. Strong vs weak resume
def test_strong_resume_scores_higher_than_weak_resume_in_readiness_mode():
    strong = score_resume(_strong_profile(), None)
    weak = score_resume(_weak_profile(), None)

    assert strong.ats_score > weak.ats_score


def test_empty_profile_scores_at_or_near_the_bottom():
    result = score_resume(_empty_profile(), None)

    assert result.ats_score <= 20


# 4 / 5 / 6. Strong / poor / partial JD match
def test_strong_jd_match_scores_high():
    """A resume that genuinely covers the JD's core skills (Python, PyTorch, Docker,
    Kubernetes, ML, recommendation systems) should score strongly even though it
    lacks the JD's explicitly optional "plus" skills (AWS/cloud/TensorFlow)."""
    result = score_resume(_strong_profile(), JD_ML_ROLE)
    poor = score_resume(
        CandidateProfile(
            identity=CandidateIdentity(full_name="Jane Doe"),
            skills=[Skill(name="Watercolor Painting")],
        ),
        JD_ML_ROLE,
    )

    assert result.mode == "jd_match"
    assert result.ats_score >= 65
    assert result.ats_score > poor.ats_score
    assert "machine learning" in result.matched_keywords
    assert "python" in result.matched_keywords


def test_poor_jd_match_scores_low():
    unrelated = CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe"),
        skills=[Skill(name="Watercolor Painting")],
        professional_summary="Professional painter and art teacher.",
    )

    result = score_resume(unrelated, JD_ML_ROLE)

    assert result.ats_score <= 30


def test_partial_jd_match_scores_between_poor_and_strong():
    partial = CandidateProfile(
        identity=CandidateIdentity(full_name="Jane Doe"),
        skills=[Skill(name="Python")],
        professional_summary="Backend developer.",
    )

    strong = score_resume(_strong_profile(), JD_ML_ROLE)
    poor = score_resume(
        CandidateProfile(identity=CandidateIdentity(full_name="Jane Doe")), JD_ML_ROLE
    )
    result = score_resume(partial, JD_ML_ROLE)

    assert poor.ats_score < result.ats_score < strong.ats_score


# 7. Missing important skills
def test_missing_skills_are_reported_when_jd_requires_unlisted_skills():
    result = score_resume(_weak_profile(), JD_ML_ROLE)

    assert "python" in result.missing_skills or "kubernetes" in result.missing_skills


# 8. Missing sections
def test_missing_sections_are_flagged_and_lower_the_score():
    complete = score_resume(_strong_profile(), None)
    missing_sections_profile = _strong_profile().model_copy(
        update={"education": [], "certifications": [], "projects": []}
    )
    incomplete = score_resume(missing_sections_profile, None)

    assert any("missing" in item.lower() for item in incomplete.section_feedback)
    assert incomplete.ats_score < complete.ats_score


# 9. Projects contributing to relevance
def test_relevant_projects_increase_jd_match_score_over_no_projects():
    with_projects = score_resume(_strong_profile(), JD_ML_ROLE)
    without_projects = score_resume(_strong_profile().model_copy(update={"projects": []}), JD_ML_ROLE)

    assert with_projects.ats_score > without_projects.ats_score
    assert any("no projects" in item.lower() for item in without_projects.project_feedback)


# 10. Relevant experience contributing to score
def test_relevant_experience_increases_jd_match_score_over_no_experience():
    with_experience = score_resume(_strong_profile(), JD_ML_ROLE)
    without_experience = score_resume(_strong_profile().model_copy(update={"experience": []}), JD_ML_ROLE)

    assert with_experience.ats_score > without_experience.ats_score
    assert any("no work experience" in item.lower() for item in without_experience.experience_feedback)


# 11. Measurable achievements
def test_measurable_achievements_increase_score_over_none():
    with_claims = score_resume(_strong_profile(), None)
    without_claims = score_resume(_strong_profile().model_copy(update={"claims": []}), None)

    assert with_claims.ats_score > without_claims.ats_score
    assert any("no measurable" in item.lower() for item in without_claims.measurable_impact_feedback)


# 12 / 13. Score bounds
def test_score_lower_bound_is_zero():
    result = score_resume(_empty_profile(), None)

    assert result.ats_score >= 0


def test_score_upper_bound_is_100():
    result = score_resume(_strong_profile(), JD_ML_ROLE)

    assert result.ats_score <= 100


@pytest.mark.parametrize("job_description", [None, JD_ML_ROLE])
def test_score_always_within_bounds(job_description):
    for profile in (_empty_profile(), _weak_profile(), _strong_profile()):
        result = score_resume(profile, job_description)
        assert 0 <= result.ats_score <= 100


# 14. Deterministic / reproducible scoring
def test_scoring_is_deterministic_across_repeated_calls():
    profile = _strong_profile()

    first = score_resume(profile, JD_ML_ROLE)
    second = score_resume(profile, JD_ML_ROLE)

    assert first == second


def test_readiness_scoring_is_deterministic_across_repeated_calls():
    profile = _weak_profile()

    first = score_resume(profile, None)
    second = score_resume(profile, None)

    assert first == second


# 16. Invalid/oversized job description
def test_oversized_job_description_raises_invalid_job_description_error():
    with pytest.raises(InvalidJobDescriptionError):
        score_resume(_strong_profile(), "x" * 20_001)


def test_job_description_at_the_limit_is_accepted():
    result = score_resume(_strong_profile(), "python " * 2857)  # ~19,999 chars

    assert result.mode == "jd_match"


def test_ats_score_never_exposes_internal_reasoning_fields():
    result = score_resume(_strong_profile(), JD_ML_ROLE)

    assert not hasattr(result, "reasoning")
    assert not hasattr(result, "chain_of_thought")
