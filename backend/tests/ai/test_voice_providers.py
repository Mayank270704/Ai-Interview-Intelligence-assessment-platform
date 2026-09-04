"""Tests for Gemini voice (speech-to-text / text-to-speech) provider implementations.

The voice providers share the Gemini client cache with the LLM provider, so
the client is patched where it is actually constructed.
"""

import pytest
from unittest.mock import MagicMock, patch


from app.ai.llm.gemini_provider import LLMUnavailableError
from app.ai.voice.gemini_voice_provider import (
    GeminiSpeechToTextProvider,
    GeminiTextToSpeechProvider,
)

STT_MODEL = "gemini-3.6-flash"
TTS_MODEL = "gemini-2.5-flash-preview-tts"

VALID_PROFILE_JSON = (
    '{"identity":{"full_name":null,"email":null,"phone":null,"location":null,'
    '"resume_evidence":null},"professional_summary":null,"education":[],"skills":[],'
    '"technologies":[],"experience":[],"projects":[],"certifications":[],'
    '"achievements":[],"claims":[],"languages":[]}'
)


# ---------------------------------------------------------------------------
# GeminiSpeechToTextProvider
# ---------------------------------------------------------------------------


def test_stt_provider_initialization_success():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        provider = GeminiSpeechToTextProvider(api_key="test-key", model=STT_MODEL)

        assert provider.model == STT_MODEL
        assert mock_client.call_args.kwargs["api_key"] == "test-key"


def test_stt_provider_initialization_missing_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiSpeechToTextProvider(api_key=None, model=STT_MODEL)


def test_stt_provider_initialization_missing_model():
    with pytest.raises(ValueError, match="GEMINI_MODEL is required"):
        GeminiSpeechToTextProvider(api_key="test-key", model=None)


def test_stt_provider_transcribe_success():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "  I fine-tuned BERT on the dataset.  "
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiSpeechToTextProvider(api_key="test-key", model=STT_MODEL)
        result = provider.transcribe(b"fake-audio-bytes", "audio/wav")

        assert result == "I fine-tuned BERT on the dataset."
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == STT_MODEL


def test_stt_provider_sends_no_reasoning_budget():
    """A reasoning budget makes the model prefix its own preamble to the transcript.

    Observed against the live API: with a thinking level set, transcription came
    back as "thought
<the actual words>". Transcription has to return the spoken
    words and nothing else, so this call must carry no thinking configuration.
    """
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.GEMINI_THINKING_LEVEL", "low"
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "I fine-tuned BERT on the dataset."
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiSpeechToTextProvider(api_key="test-key", model=STT_MODEL)
        provider.transcribe(b"fake-audio-bytes", "audio/wav")

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.thinking_config is None
        assert config.automatic_function_calling.disable is True


def test_structured_generation_keeps_its_reasoning_budget():
    """The reasoning calls are the ones the thinking level is actually for."""
    from app.ai.llm.gemini_provider import GeminiProvider
    from app.schemas.resume import CandidateProfile

    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class, patch(
        "app.ai.llm.gemini_provider.GEMINI_THINKING_LEVEL", "low"
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = VALID_PROFILE_JSON
        mock_client.models.generate_content.return_value = mock_response

        GeminiProvider(api_key="test-key", model=STT_MODEL).generate_structured(
            "Test prompt", CandidateProfile
        )

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        # The SDK normalises the level into its own enum.
        assert str(config.thinking_config.thinking_level).lower().endswith("low")


def test_stt_provider_transcribe_handles_api_error():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiSpeechToTextProvider(api_key="test-key", model=STT_MODEL)

        with pytest.raises(LLMUnavailableError, match="Gemini transcription failed"):
            provider.transcribe(b"fake-audio-bytes", "audio/wav")


def test_stt_provider_transcribe_rejects_empty_transcript():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "   "
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiSpeechToTextProvider(api_key="test-key", model=STT_MODEL)

        with pytest.raises(LLMUnavailableError, match="returned no text"):
            provider.transcribe(b"fake-audio-bytes", "audio/wav")


# ---------------------------------------------------------------------------
# GeminiTextToSpeechProvider
# ---------------------------------------------------------------------------


def test_tts_provider_initialization_success():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client:
        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model=TTS_MODEL
        )

        assert provider.model == TTS_MODEL
        assert mock_client.call_args.kwargs["api_key"] == "test-key"


def test_tts_provider_initialization_missing_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiTextToSpeechProvider(api_key=None, model=TTS_MODEL)


def test_tts_provider_initialization_missing_model():
    with pytest.raises(ValueError, match="GEMINI_TTS_MODEL is required"):
        GeminiTextToSpeechProvider(api_key="test-key", model=None)


def _mock_audio_response(data: bytes = b"raw-pcm-audio", mime_type: str = "audio/pcm"):
    part = MagicMock()
    part.inline_data.data = data
    part.inline_data.mime_type = mime_type
    response = MagicMock()
    response.candidates = [MagicMock(content=MagicMock(parts=[part]))]
    return response


def test_tts_provider_synthesize_success():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = _mock_audio_response()

        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model=TTS_MODEL
        )
        audio_bytes, mime_type = provider.synthesize("How did you build the sentiment model?")

        assert audio_bytes == b"raw-pcm-audio"
        assert mime_type == "audio/pcm"
        mock_client.models.generate_content.assert_called_once()


def test_tts_provider_synthesize_rejects_empty_text():
    with patch("app.ai.llm.gemini_provider.genai.Client"):
        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model=TTS_MODEL
        )

        with pytest.raises(ValueError, match="Cannot synthesize empty text"):
            provider.synthesize("   ")


def test_tts_provider_synthesize_handles_api_error():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model=TTS_MODEL
        )

        with pytest.raises(LLMUnavailableError, match="Gemini speech synthesis failed"):
            provider.synthesize("Hello")


def test_tts_provider_synthesize_rejects_empty_audio_response():
    with patch("app.ai.llm.gemini_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = _mock_audio_response(data=b"")

        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model=TTS_MODEL
        )

        with pytest.raises(LLMUnavailableError, match="returned no audio"):
            provider.synthesize("Hello")
