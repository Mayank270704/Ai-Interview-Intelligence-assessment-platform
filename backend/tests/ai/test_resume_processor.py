"""Tests for resume processor."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.resume_intelligence.processor import ResumeProcessor
from app.schemas.resume import CandidateProfile, CandidateIdentity


@pytest.fixture
def sample_candidate_profile_dict():
    """Fixture with a sample candidate profile as dict."""
    return {
        "identity": {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-0123",
            "location": "San Francisco, CA",
        },
        "professional_summary": "Senior Software Engineer with 8 years of experience",
        "education": [
            {
                "institution": "Stanford University",
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "end_date": "2015",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "Expert"},
            {"name": "Machine Learning", "proficiency": "Advanced"},
        ],
        "technologies": [
            {"name": "PyTorch", "category": "Framework"},
            {"name": "TensorFlow", "category": "Framework"},
        ],
        "experience": [
            {
                "company": "Google",
                "position": "Senior Engineer",
                "start_date": "2020",
                "end_date": "Present",
                "description": "Lead ML infrastructure team",
            }
        ],
        "projects": [
            {
                "name": "ML Pipeline",
                "description": "Built an ML pipeline",
                "technologies": ["Python", "PyTorch"],
            }
        ],
        "certifications": [],
        "achievements": [
            {
                "title": "Best Paper Award",
                "description": "NeurIPS 2021",
            }
        ],
        "claims": [
            {
                "claim_text": "Improved model accuracy by 18%",
                "category": "quantitative",
                "context": "ML Pipeline project",
                "resume_evidence": "Improved model accuracy by 18%",
            }
        ],
        "languages": ["Python", "Java"],
    }


def test_resume_processor_initialization():
    """Test that ResumeProcessor initializes correctly."""
    processor = ResumeProcessor()
    assert processor.llm_client is not None


@patch("app.ai.resume_intelligence.processor.LLMClient")
@patch("app.ai.resume_intelligence.processor.extract_text_from_pdf")
def test_process_resume_success(mock_extract_text, mock_llm_client, sample_candidate_profile_dict):
    """Test successful resume processing with mocked Gemini."""
    # Mock PDF extraction
    mock_extract_text.return_value = "John Doe\nSenior Engineer\nSkills: Python, ML"

    # Mock Gemini response
    mock_llm = MagicMock()
    mock_llm_client.return_value = mock_llm

    # Create a CandidateProfile instance from the sample dict
    sample_profile = CandidateProfile(**sample_candidate_profile_dict)

    # Mock the structured output method
    mock_llm.generate_structured.return_value = sample_profile

    processor = ResumeProcessor()
    processor.llm_client = mock_llm

    # Process resume
    pdf_bytes = b"fake pdf content"
    result = processor.process_resume(pdf_bytes)

    # Verify
    assert result.identity.full_name == "John Doe"
    assert result.identity.email == "john@example.com"
    assert len(result.skills) > 0
    assert result.skills[0].name == "Python"


@patch("app.ai.resume_intelligence.processor.extract_text_from_pdf")
def test_process_resume_handles_extraction_error(mock_extract_text):
    """Test that ResumeProcessor handles PDF extraction errors."""
    from app.ai.resume_intelligence.pdf_processor import PDFExtractionError

    mock_extract_text.side_effect = PDFExtractionError("Invalid PDF")

    processor = ResumeProcessor()

    with pytest.raises(PDFExtractionError):
        processor.process_resume(b"invalid pdf")


@patch("app.ai.resume_intelligence.processor.LLMClient")
@patch("app.ai.resume_intelligence.processor.extract_text_from_pdf")
def test_process_resume_handles_gemini_error(mock_extract_text, mock_llm_client):
    """Test that ResumeProcessor handles Gemini errors."""
    mock_extract_text.return_value = "Resume text"

    mock_llm = MagicMock()
    mock_llm_client.return_value = mock_llm
    mock_llm.generate_structured.side_effect = ValueError("Invalid response")

    processor = ResumeProcessor()
    processor.llm_client = mock_llm

    with pytest.raises(ValueError, match="Failed to analyze resume"):
        processor.process_resume(b"fake pdf")


def test_build_analysis_prompt():
    """Test that the analysis prompt is built correctly."""
    test_text = "John Doe\nSkills: Python, Java\nExperience: 5 years"
    prompt = ResumeProcessor._build_analysis_prompt(test_text)

    assert "John Doe" in prompt
    assert "Python" in prompt
    assert "Analyze the following resume" in prompt
    assert "CandidateProfile" in prompt


@patch("app.ai.resume_intelligence.processor.LLMClient")
@patch("app.ai.resume_intelligence.processor.extract_text_from_pdf")
@patch("app.ai.resume_intelligence.processor.clean_resume_text")
def test_process_resume_pipeline_order(
    mock_clean, mock_extract_text, mock_llm_client, sample_candidate_profile_dict
):
    """Test that resume processing follows the correct pipeline order."""
    # Setup mocks
    raw_text = "Raw resume text"
    cleaned_text = "Cleaned resume text"

    mock_extract_text.return_value = raw_text
    mock_clean.return_value = cleaned_text

    mock_llm = MagicMock()
    mock_llm_client.return_value = mock_llm
    sample_profile = CandidateProfile(**sample_candidate_profile_dict)
    mock_llm.generate_structured.return_value = sample_profile

    processor = ResumeProcessor()
    processor.llm_client = mock_llm

    # Process
    processor.process_resume(b"fake pdf")

    # Verify call order
    mock_extract_text.assert_called_once()
    mock_clean.assert_called_once_with(raw_text)
    mock_llm.generate_structured.assert_called_once()

    # Verify cleaned text was used in prompt
    call_args = mock_llm.generate_structured.call_args
    prompt = call_args[0][0]
    assert cleaned_text in prompt
