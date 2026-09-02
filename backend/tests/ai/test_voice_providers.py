"""Tests for Gemini voice (speech-to-text / text-to-speech) provider implementations."""

import pytest
from unittest.mock import MagicMock, patch


from app.ai.voice.gemini_voice_provider import (
    GeminiSpeechToTextProvider,
    GeminiTextToSpeechProvider,
)


# ---------------------------------------------------------------------------
# GeminiSpeechToTextProvider
# ---------------------------------------------------------------------------


def test_stt_provider_initialization_success():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client:
        provider = GeminiSpeechToTextProvider(api_key="test-key", model="gemini-2.0-flash")

        assert provider.model == "gemini-2.0-flash"
        mock_client.assert_called_once_with(api_key="test-key")


def test_stt_provider_initialization_missing_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiSpeechToTextProvider(api_key=None, model="gemini-2.0-flash")


def test_stt_provider_initialization_missing_model():
    with pytest.raises(ValueError, match="GEMINI_MODEL is required"):
        GeminiSpeechToTextProvider(api_key="test-key", model=None)


def test_stt_provider_transcribe_success():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "  I fine-tuned BERT on the dataset.  "
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiSpeechToTextProvider(api_key="test-key", model="gemini-2.0-flash")
        result = provider.transcribe(b"fake-audio-bytes", "audio/wav")

        assert result == "I fine-tuned BERT on the dataset."
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.0-flash"


def test_stt_provider_transcribe_handles_api_error():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiSpeechToTextProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(RuntimeError, match="Gemini transcription failed"):
            provider.transcribe(b"fake-audio-bytes", "audio/wav")


def test_stt_provider_transcribe_rejects_empty_transcript():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "   "
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiSpeechToTextProvider(api_key="test-key", model="gemini-2.0-flash")

        with pytest.raises(RuntimeError, match="returned no text"):
            provider.transcribe(b"fake-audio-bytes", "audio/wav")


# ---------------------------------------------------------------------------
# GeminiTextToSpeechProvider
# ---------------------------------------------------------------------------


def test_tts_provider_initialization_success():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client:
        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model="gemini-2.5-flash-preview-tts"
        )

        assert provider.model == "gemini-2.5-flash-preview-tts"
        mock_client.assert_called_once_with(api_key="test-key")


def test_tts_provider_initialization_missing_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiTextToSpeechProvider(api_key=None, model="gemini-2.5-flash-preview-tts")


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
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = _mock_audio_response()

        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model="gemini-2.5-flash-preview-tts"
        )
        audio_bytes, mime_type = provider.synthesize("How did you build the sentiment model?")

        assert audio_bytes == b"raw-pcm-audio"
        assert mime_type == "audio/pcm"
        mock_client.models.generate_content.assert_called_once()


def test_tts_provider_synthesize_rejects_empty_text():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client"):
        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model="gemini-2.5-flash-preview-tts"
        )

        with pytest.raises(ValueError, match="Cannot synthesize empty text"):
            provider.synthesize("   ")


def test_tts_provider_synthesize_handles_api_error():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model="gemini-2.5-flash-preview-tts"
        )

        with pytest.raises(RuntimeError, match="Gemini speech synthesis failed"):
            provider.synthesize("Hello")


def test_tts_provider_synthesize_rejects_empty_audio_response():
    with patch("app.ai.voice.gemini_voice_provider.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = _mock_audio_response(data=b"")

        provider = GeminiTextToSpeechProvider(
            api_key="test-key", model="gemini-2.5-flash-preview-tts"
        )

        with pytest.raises(RuntimeError, match="returned no audio"):
            provider.synthesize("Hello")
