"""Tests for the voice provider abstraction and client configuration."""

import pytest
from unittest.mock import MagicMock, patch

from app.ai.voice.client import VoiceClient, _load_stt_provider, _load_tts_provider
from app.ai.voice.provider import SpeechToTextProvider, TextToSpeechProvider


def test_load_stt_provider_gemini_success():
    with patch("app.ai.voice.client.VOICE_PROVIDER", "gemini"), patch(
        "app.ai.voice.client.GEMINI_API_KEY", "test-key"
    ), patch("app.ai.voice.client.GEMINI_MODEL", "gemini-2.0-flash"), patch(
        "app.ai.voice.client.GeminiSpeechToTextProvider"
    ) as mock_provider:
        mock_instance = MagicMock()
        mock_provider.return_value = mock_instance

        provider = _load_stt_provider()

        assert provider == mock_instance
        mock_provider.assert_called_once_with(api_key="test-key", model="gemini-2.0-flash")


def test_load_stt_provider_missing_api_key():
    with patch("app.ai.voice.client.VOICE_PROVIDER", "gemini"), patch(
        "app.ai.voice.client.GEMINI_API_KEY", None
    ):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
            _load_stt_provider()


def test_load_stt_provider_unknown():
    with patch("app.ai.voice.client.VOICE_PROVIDER", "unknown"):
        with pytest.raises(ValueError, match="Unknown VOICE_PROVIDER"):
            _load_stt_provider()


def test_load_tts_provider_gemini_success():
    with patch("app.ai.voice.client.VOICE_PROVIDER", "gemini"), patch(
        "app.ai.voice.client.GEMINI_API_KEY", "test-key"
    ), patch("app.ai.voice.client.GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"), patch(
        "app.ai.voice.client.GeminiTextToSpeechProvider"
    ) as mock_provider:
        mock_instance = MagicMock()
        mock_provider.return_value = mock_instance

        provider = _load_tts_provider()

        assert provider == mock_instance
        mock_provider.assert_called_once_with(
            api_key="test-key", model="gemini-2.5-flash-preview-tts"
        )


def test_load_tts_provider_missing_api_key():
    with patch("app.ai.voice.client.VOICE_PROVIDER", "gemini"), patch(
        "app.ai.voice.client.GEMINI_API_KEY", None
    ):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
            _load_tts_provider()


def test_load_tts_provider_unknown():
    with patch("app.ai.voice.client.VOICE_PROVIDER", "unknown"):
        with pytest.raises(ValueError, match="Unknown VOICE_PROVIDER"):
            _load_tts_provider()


def test_voice_client_initialization():
    with patch("app.ai.voice.client._load_stt_provider") as mock_stt, patch(
        "app.ai.voice.client._load_tts_provider"
    ) as mock_tts:
        mock_stt_instance = MagicMock(spec=SpeechToTextProvider)
        mock_tts_instance = MagicMock(spec=TextToSpeechProvider)
        mock_stt.return_value = mock_stt_instance
        mock_tts.return_value = mock_tts_instance

        client = VoiceClient()

        assert client.stt_provider == mock_stt_instance
        assert client.tts_provider == mock_tts_instance


def test_voice_client_transcribe_delegates_to_provider():
    with patch("app.ai.voice.client._load_stt_provider") as mock_stt, patch(
        "app.ai.voice.client._load_tts_provider"
    ):
        mock_stt_instance = MagicMock(spec=SpeechToTextProvider)
        mock_stt_instance.transcribe.return_value = "Transcribed text"
        mock_stt.return_value = mock_stt_instance

        client = VoiceClient()
        result = client.transcribe(b"audio-bytes", "audio/wav")

        assert result == "Transcribed text"
        mock_stt_instance.transcribe.assert_called_once_with(b"audio-bytes", "audio/wav")


def test_voice_client_synthesize_delegates_to_provider():
    with patch("app.ai.voice.client._load_stt_provider"), patch(
        "app.ai.voice.client._load_tts_provider"
    ) as mock_tts:
        mock_tts_instance = MagicMock(spec=TextToSpeechProvider)
        mock_tts_instance.synthesize.return_value = (b"audio-bytes", "audio/pcm")
        mock_tts.return_value = mock_tts_instance

        client = VoiceClient()
        result = client.synthesize("Hello")

        assert result == (b"audio-bytes", "audio/pcm")
        mock_tts_instance.synthesize.assert_called_once_with("Hello")


def test_voice_client_propagates_provider_errors():
    with patch("app.ai.voice.client._load_stt_provider") as mock_stt, patch(
        "app.ai.voice.client._load_tts_provider"
    ):
        mock_stt_instance = MagicMock(spec=SpeechToTextProvider)
        mock_stt_instance.transcribe.side_effect = RuntimeError("API failure")
        mock_stt.return_value = mock_stt_instance

        client = VoiceClient()

        with pytest.raises(RuntimeError, match="API failure"):
            client.transcribe(b"audio-bytes", "audio/wav")
