"""Tests for Gemini provider implementation."""

import pytest
from unittest.mock import MagicMock, patch

from google.genai import errors as genai_errors

from app.ai.llm.gemini_provider import GeminiProvider, LLMUnavailableError
from app.schemas.resume import CandidateProfile

MODEL = "gemini-3.6-flash"

VALID_PROFILE_JSON = (
    '{"identity":{"full_name":null,"email":null,"phone":null,"location":null,'
    '"resume_evidence":null},"professional_summary":null,"education":[],"skills":[],'
    '"technologies":[],"experience":[],"projects":[],"certifications":[],'
    '"achievements":[],"claims":[],"languages":[]}'
)


def api_error(status_code: int) -> genai_errors.APIError:
    return genai_errors.APIError(status_code, {"error": {"message": "upstream"}})


def test_gemini_provider_initialization_success():
    """Test successful Gemini provider initialization."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        provider = GeminiProvider(api_key="test-key", model=MODEL)

        assert provider.model == MODEL
        assert mock_client.call_args.kwargs["api_key"] == "test-key"


def test_gemini_provider_reuses_one_client_per_api_key():
    """A second provider on the same key must not build a second client."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        first = GeminiProvider(api_key="shared-key", model=MODEL)
        second = GeminiProvider(api_key="shared-key", model=MODEL)

        assert first.client is second.client
        mock_client.assert_called_once()


def test_gemini_provider_initialization_missing_api_key():
    """Test Gemini provider initialization fails without API key."""
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiProvider(api_key=None, model=MODEL)


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

        provider = GeminiProvider(api_key="test-key", model=MODEL)
        result = provider.generate("Test prompt")

        assert result == "Generated response"
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == MODEL
        assert call_args.kwargs["contents"] == "Test prompt"


def test_gemini_provider_disables_automatic_function_calling():
    """No tools are ever passed, so the SDK's call loop is explicitly disabled."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = MagicMock(text="ok")

        GeminiProvider(api_key="test-key", model=MODEL).generate("Test prompt")

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.automatic_function_calling.disable is True


def test_gemini_provider_generate_handles_errors():
    """Test Gemini provider handles generation errors."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError, match="Gemini generation failed"):
            provider.generate("Test prompt")


def test_gemini_provider_generate_structured_success():
    """Test successful structured generation with Gemini provider."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = VALID_PROFILE_JSON
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)
        result = provider.generate_structured("Test prompt", CandidateProfile)

        assert isinstance(result, CandidateProfile)
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == MODEL
        assert call_args.kwargs["contents"] == "Test prompt"
        assert call_args.kwargs["config"].response_schema is CandidateProfile


def test_gemini_provider_generate_structured_handles_api_error():
    """Test Gemini provider handles structured generation API errors."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError, match="Gemini structured generation failed"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_generate_structured_handles_validation_error():
    """Test Gemini provider handles validation errors in structured generation."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"invalid": "data"}'
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(ValueError, match="Failed to parse response as"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_reports_an_empty_response_as_unavailable():
    """A truncated or filtered response has no text; that is not a parse failure."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = None
        mock_response.candidates = [MagicMock(finish_reason="MAX_TOKENS")]
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError, match="MAX_TOKENS"):
            provider.generate_structured("Test prompt", CandidateProfile)


def test_gemini_provider_retries_a_transient_upstream_failure():
    """A 503 means the request was never processed, so re-sending it is safe."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.time.sleep"
    ) as mock_sleep:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        succeeded = MagicMock()
        succeeded.text = VALID_PROFILE_JSON
        mock_client.models.generate_content.side_effect = [api_error(503), succeeded]

        provider = GeminiProvider(api_key="test-key", model=MODEL)
        result = provider.generate_structured("Test prompt", CandidateProfile)

        assert isinstance(result, CandidateProfile)
        assert mock_client.models.generate_content.call_count == 2
        mock_sleep.assert_called_once()


def test_gemini_provider_does_not_retry_a_client_error():
    """A 400 fails identically every time; retrying only wastes the caller's time."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = api_error(400)

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError):
            provider.generate_structured("Test prompt", CandidateProfile)
        assert mock_client.models.generate_content.call_count == 1


def test_gemini_provider_gives_up_after_the_retry_budget():
    """Retrying is bounded: a persistent outage must surface, not loop forever."""
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.time.sleep"
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = api_error(503)

        provider = GeminiProvider(api_key="test-key", model=MODEL)

        with pytest.raises(LLMUnavailableError):
            provider.generate_structured("Test prompt", CandidateProfile)
        assert mock_client.models.generate_content.call_count == 3
