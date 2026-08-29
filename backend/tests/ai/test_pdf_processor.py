"""Tests for PDF extraction and text cleaning."""

import pytest

from app.ai.resume_intelligence.pdf_processor import (
    extract_text_from_pdf,
    clean_resume_text,
    PDFExtractionError,
)


def test_extract_text_from_empty_bytes():
    """Test that empty PDF bytes raise an error."""
    with pytest.raises(PDFExtractionError, match="PDF is empty"):
        extract_text_from_pdf(b"")


def test_extract_text_from_invalid_pdf():
    """Test that invalid PDF bytes raise an error."""
    invalid_pdf = b"This is not a valid PDF"
    with pytest.raises(PDFExtractionError):
        extract_text_from_pdf(invalid_pdf)


def test_clean_resume_text_removes_extra_spaces():
    """Test that clean_resume_text removes extra spaces."""
    text = "John    Doe    Senior    Engineer"
    cleaned = clean_resume_text(text)
    assert cleaned == "John Doe Senior Engineer"


def test_clean_resume_text_normalizes_newlines():
    """Test that multiple newlines are normalized."""
    text = "Line 1\n\n\n\nLine 2\n\n\n\nLine 3"
    cleaned = clean_resume_text(text)
    assert cleaned == "Line 1\nLine 2\nLine 3"


def test_clean_resume_text_removes_empty_lines():
    """Test that empty lines are removed."""
    text = "Line 1\n\nLine 2\n\nLine 3"
    cleaned = clean_resume_text(text)
    assert "Line 1" in cleaned
    assert "Line 2" in cleaned
    assert "Line 3" in cleaned


def test_clean_resume_text_strips_whitespace():
    """Test that leading/trailing whitespace is removed from lines."""
    text = "  Line 1  \n  Line 2  \n  Line 3  "
    cleaned = clean_resume_text(text)
    assert cleaned == "Line 1\nLine 2\nLine 3"


def test_clean_resume_text_preserves_content():
    """Test that important content is preserved."""
    text = "Skills: Python, Java, SQL\nExperience: 5 years"
    cleaned = clean_resume_text(text)
    assert "Python" in cleaned
    assert "Java" in cleaned
    assert "SQL" in cleaned
    assert "5 years" in cleaned
