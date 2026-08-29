"""Tests for candidate profile schemas."""

import pytest

from app.schemas.resume import (
    CandidateProfile,
    CandidateIdentity,
    Education,
    Skill,
    Technology,
    Experience,
    Project,
    Certification,
    Achievement,
    Claim,
)


def test_candidate_identity_creation():
    """Test creating a candidate identity."""
    identity = CandidateIdentity(
        full_name="John Doe",
        email="john@example.com",
        phone="+1-555-0123",
        location="San Francisco, CA",
    )
    assert identity.full_name == "John Doe"
    assert identity.email == "john@example.com"


def test_education_creation():
    """Test creating an education entry."""
    edu = Education(
        institution="Stanford University",
        degree="M.S.",
        field_of_study="Computer Science",
        end_date="2020",
    )
    assert edu.institution == "Stanford University"
    assert edu.degree == "M.S."


def test_skill_with_proficiency():
    """Test creating a skill with proficiency."""
    skill = Skill(name="Python", proficiency="Expert")
    assert skill.name == "Python"
    assert skill.proficiency == "Expert"


def test_technology_creation():
    """Test creating a technology entry."""
    tech = Technology(name="PyTorch", category="Framework")
    assert tech.name == "PyTorch"
    assert tech.category == "Framework"


def test_experience_creation():
    """Test creating an experience entry."""
    exp = Experience(
        company="Google",
        position="Senior Engineer",
        start_date="2020",
        end_date="Present",
    )
    assert exp.company == "Google"
    assert exp.position == "Senior Engineer"


def test_project_creation():
    """Test creating a project entry."""
    project = Project(
        name="ML Pipeline",
        technologies=["TensorFlow", "Python"],
        description="Built a machine learning pipeline",
    )
    assert project.name == "ML Pipeline"
    assert "TensorFlow" in project.technologies


def test_claim_creation():
    """Test creating a claim entry."""
    claim = Claim(
        claim_text="Improved model accuracy by 18%",
        category="quantitative",
        context="Sentiment analysis project",
        resume_evidence="Improved model accuracy by 18%",
    )
    assert claim.claim_text == "Improved model accuracy by 18%"
    assert claim.category == "quantitative"


def test_candidate_profile_creation():
    """Test creating a complete candidate profile."""
    identity = CandidateIdentity(
        full_name="Jane Doe",
        email="jane@example.com",
        location="New York, NY",
    )
    edu = Education(
        institution="MIT",
        degree="Ph.D.",
        field_of_study="AI",
    )
    skill = Skill(name="Machine Learning", proficiency="Expert")
    exp = Experience(
        company="OpenAI",
        position="Researcher",
        start_date="2021",
        end_date="Present",
    )

    profile = CandidateProfile(
        identity=identity,
        education=[edu],
        skills=[skill],
        experience=[exp],
    )

    assert profile.identity.full_name == "Jane Doe"
    assert len(profile.education) == 1
    assert len(profile.skills) == 1
    assert len(profile.experience) == 1


def test_candidate_profile_with_defaults():
    """Test that candidate profile has default empty lists."""
    identity = CandidateIdentity(full_name="Test User")
    profile = CandidateProfile(identity=identity)

    assert profile.education == []
    assert profile.skills == []
    assert profile.technologies == []
    assert profile.experience == []
    assert profile.projects == []
    assert profile.certifications == []
    assert profile.achievements == []
    assert profile.claims == []
    assert profile.languages == []


def test_claim_with_different_categories():
    """Test claims with different categories."""
    quantitative = Claim(
        claim_text="Increased revenue by 25%",
        category="quantitative",
        resume_evidence="Increased revenue by 25%",
    )
    technical = Claim(
        claim_text="Built a BERT-based system",
        category="technical",
        resume_evidence="Built a BERT-based system",
    )
    domain = Claim(
        claim_text="Expert in distributed systems",
        category="domain",
        resume_evidence="Expert in distributed systems",
    )

    assert quantitative.category == "quantitative"
    assert technical.category == "technical"
    assert domain.category == "domain"
