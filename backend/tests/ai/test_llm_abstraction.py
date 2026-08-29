"""Tests for LLM provider abstraction and configuration."""

import pytest
from unittest.mock import MagicMock, patch

from app.ai.llm.client import LLMClient, _load_provider
from app.ai.llm.provider import LLMProvider
from app.schemas.resume import CandidateProfile, CandidateIdentity


class MockProvider(LLMProvider):
    """Mock provider for testing."""

    def __init__(self):
        self.generate_calls = []
        self.generate_structured_calls = []

    def generate(self, prompt: str) -> str:
        """Mock generate implementation."""
        self.generate_calls.append(prompt)
        return "Mock response"

    def generate_structured(self, prompt: str, response_model):
        """Mock generate_structured implementation."""
        self.generate_structured_calls.append((prompt, response_model))
        # Return minimal valid instance
        if response_model == CandidateProfile:
            return CandidateProfile(identity=CandidateIdentity())
        return response_model()


def test_load_provider_gemini_success():
    """Test loading Gemini provider with valid configuration."""
    with patch("app.ai.llm.client.LLM_PROVIDER", "gemini"), patch(
        "app.ai.llm.client.GEMINI_API_KEY", "test-key"
    ), patch("app.ai.llm.client.GEMINI_MODEL", "gemini-2.0-flash"), patch(
        "app.ai.llm.client.GeminiProvider"
    ) as mock_gemini:
        mock_instance = MagicMock()
        mock_gemini.return_value = mock_instance

        provider = _load_provider()

        assert provider == mock_instance
        mock_gemini.assert_called_once_with(api_key="test-key", model="gemini-2.0-flash")


def test_load_provider_gemini_missing_api_key():
    """Test loading Gemini provider fails without API key."""
    with patch("app.ai.llm.client.LLM_PROVIDER", "gemini"), patch(
        "app.ai.llm.client.GEMINI_API_KEY", None
    ):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
            _load_provider()


def test_load_provider_unknown():
    """Test loading unknown provider fails."""
    with patch("app.ai.llm.client.LLM_PROVIDER", "unknown"):
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            _load_provider()


def test_llm_client_initialization():
    """Test LLMClient initialization."""
    with patch("app.ai.llm.client._load_provider") as mock_load:
        mock_provider = MagicMock(spec=LLMProvider)
        mock_load.return_value = mock_provider

        client = LLMClient()

        assert client.provider == mock_provider
        mock_load.assert_called_once()


def test_llm_client_generate():
    """Test LLMClient.generate delegates to provider."""
    with patch("app.ai.llm.client._load_provider") as mock_load:
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.generate.return_value = "Generated text"
        mock_load.return_value = mock_provider

        client = LLMClient()
        result = client.generate("Test prompt")

        assert result == "Generated text"
        mock_provider.generate.assert_called_once_with("Test prompt")


def test_llm_client_generate_structured():
    """Test LLMClient.generate_structured delegates to provider."""
    with patch("app.ai.llm.client._load_provider") as mock_load:
        mock_provider = MagicMock(spec=LLMProvider)
        mock_profile = CandidateProfile(identity=CandidateIdentity())
        mock_provider.generate_structured.return_value = mock_profile
        mock_load.return_value = mock_provider

        client = LLMClient()
        result = client.generate_structured("Test prompt", CandidateProfile)

        assert result == mock_profile
        mock_provider.generate_structured.assert_called_once_with(
            "Test prompt", CandidateProfile
        )


def test_llm_client_propagates_errors():
    """Test LLMClient propagates provider errors."""
    with patch("app.ai.llm.client._load_provider") as mock_load:
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.generate.side_effect = RuntimeError("API failure")
        mock_load.return_value = mock_provider

        client = LLMClient()

        with pytest.raises(RuntimeError, match="API failure"):
            client.generate("Test prompt")
