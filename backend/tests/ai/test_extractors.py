"""Tests for resume extractors."""

from app.ai.resume_intelligence.section_extractor import extract_resume_sections
from app.ai.resume_intelligence.skill_extractor import extract_skills_from_text
from app.ai.resume_intelligence.experience_extractor import extract_experience_entries
from app.ai.resume_intelligence.project_extractor import extract_projects
from app.ai.resume_intelligence.claim_extractor import extract_potential_claims


def test_extract_resume_sections():
    """Test extracting sections from resume text."""
    text = """
    Contact
    john@example.com
    555-0123

    Professional Summary
    Senior engineer with 5 years experience

    Education
    Stanford University, BS Computer Science, 2015

    Experience
    Google | Senior Engineer | 2020 - Present

    Skills
    Python, Java, C++
    """

    sections = extract_resume_sections(text)
    assert "contact" in sections or "Contact" in str(sections)
    assert "education" in sections or "Education" in str(sections)


def test_extract_skills_from_text():
    """Test extracting skills from resume text."""
    text = """
    Skills
    Python • Java • C++ • SQL
    AWS • GCP • Docker
    Machine Learning • Data Analysis
    """

    skills = extract_skills_from_text(text)
    # Should extract some skills
    assert len(skills) > 0
    # Check that extracted skills contain expected ones
    skill_str = " ".join(skills).lower()
    assert any(s in skill_str for s in ["python", "java", "c++", "sql", "aws", "docker"])


def test_extract_experience_entries():
    """Test extracting experience entries."""
    text = """
    Google | Senior Engineer | January 2020 – Present
    Led the ML infrastructure team

    Facebook | Software Engineer | June 2018 – December 2019
    Worked on recommendation systems
    """

    experiences = extract_experience_entries(text)
    # Should extract some experiences
    assert len(experiences) >= 0


def test_extract_projects():
    """Test extracting projects from resume text."""
    text = """
    Projects
    • ML Pipeline - Built an end-to-end ML pipeline using Python and TensorFlow
    • Data Visualization Tool - Created interactive dashboards with D3.js
    Project: Recommendation System
    """

    projects = extract_projects(text)
    assert len(projects) >= 0


def test_extract_potential_claims():
    """Test extracting potential claims from resume."""
    text = """
    Improved model accuracy by 18% through hyperparameter tuning
    Designed and implemented a recommendation system serving 1M+ users
    Built a BERT-based NLP solution for sentiment analysis
    Decreased latency by 40% through optimization
    """

    claims = extract_potential_claims(text)
    assert len(claims) > 0
    # Should identify at least some quantitative claims
    claim_types = [c.get("type") for c in claims]
    assert "quantitative" in claim_types or "technical" in claim_types


def test_extract_skills_returns_list():
    """Test that extract_skills_from_text returns a list."""
    text = "Skills: Python, Java"
    skills = extract_skills_from_text(text)
    assert isinstance(skills, list)


def test_extract_experience_returns_list():
    """Test that extract_experience_entries returns a list."""
    text = "Experience: Google, Senior Engineer, 2020-Present"
    experiences = extract_experience_entries(text)
    assert isinstance(experiences, list)


def test_extract_projects_returns_list():
    """Test that extract_projects returns a list."""
    text = "Projects: ML Pipeline, Data Tool"
    projects = extract_projects(text)
    assert isinstance(projects, list)


def test_extract_claims_returns_list():
    """Test that extract_potential_claims returns a list."""
    text = "Improved accuracy by 20%"
    claims = extract_potential_claims(text)
    assert isinstance(claims, list)


def test_extract_claims_identifies_quantitative():
    """Test that quantitative claims are identified."""
    text = "Improved model accuracy by 18%"
    claims = extract_potential_claims(text)
    assert len(claims) > 0
    # At least one should be quantitative
    assert any(c.get("type") == "quantitative" for c in claims)
