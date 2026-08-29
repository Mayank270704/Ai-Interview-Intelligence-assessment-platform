"""Tests for Gemini provider implementation."""

import pytest
from unittest.mock import MagicMock, patch

from app.ai.llm.gemini_provider import GeminiProvider
from app.schemas.resume import CandidateProfile, CandidateIdentity


def test_gemini_provider_initialization_success():
    """Test successful Gemini provider initialization."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        assert provider.model == "gemini-2.0-flash"
        mock_client.assert_called_once_with(api_key="test-key")


def test_gemini_provider_initialization_missing_api_key():
    """Test Gemini provider initialization fails without API key."""
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiProvider(api_key=None, model="gemini-2.0-flash")


def test_gemini_provider_initialization_missing_model():
    """Test Gemini provider initialization fails without model."""
    with pytest.raises(ValueError, match="GEMINI_MODEL is required"):
        GeminiProvider(api_key="test-key", model=None)


def test_gemini_provider_generate_success():
    """Test successful text generation with Gemini provider."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
        result = provider.generate("Test prompt")

        assert result == "Generated response"
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents="Test prompt",
        )


def test_gemini_provider_generate_handles_errors():
    """Test Gemini provider handles generation errors."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(RuntimeError, match="Gemini generation failed"):
            provider.generate("Test prompt")


def test_gemini_provider_generate_structured_success():
    """Test successful structured generation with Gemini provider."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.types.GenerateContentConfig"
    ) as mock_config:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create a minimal valid JSON response
        mock_response = MagicMock()
        mock_response.text = '{"identity":{"full_name":null,"email":null,"phone":null,"location":null,"resume_evidence":null},"professional_summary":null,"education":[],"skills":[],"technologies":[],"experience":[],"projects":[],"certifications":[],"achievements":[],"claims":[],"languages":[]}'
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
        result = provider.generate_structured("Test prompt", CandidateProfile)

        assert isinstance(result, CandidateProfile)
        mock_client.models.generate_content.assert_called_once()

        # Verify config was created with correct parameters
        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-2.0-flash"
        assert call_args[1]["contents"] == "Test prompt"


def test_gemini_provider_generate_structured_handles_api_error():
    """Test Gemini provider handles structured generation API errors."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(RuntimeError, match="Gemini structured generation failed"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_generate_structured_handles_validation_error():
    """Test Gemini provider handles validation errors in structured generation."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return invalid JSON
        mock_response = MagicMock()
        mock_response.text = '{"invalid": "data"}'
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(ValueError, match="Failed to parse response as"):
            provider.generate_structured("Test prompt", CandidateProfile)
