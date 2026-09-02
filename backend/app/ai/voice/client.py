"""Voice client - provider-independent interface for speech-to-text and text-to-speech."""

from app.ai.voice.gemini_voice_provider import (
    GeminiSpeechToTextProvider,
    GeminiTextToSpeechProvider,
)
from app.ai.voice.provider import SpeechToTextProvider, TextToSpeechProvider
from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TTS_MODEL,
    VOICE_PROVIDER,
)


def _load_stt_provider() -> SpeechToTextProvider:
    """Load the configured speech-to-text provider."""
    if VOICE_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        return GeminiSpeechToTextProvider(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
    raise ValueError(f"Unknown VOICE_PROVIDER: {VOICE_PROVIDER}. Supported: 'gemini'")


def _load_tts_provider() -> TextToSpeechProvider:
    """Load the configured text-to-speech provider."""
    if VOICE_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        return GeminiTextToSpeechProvider(api_key=GEMINI_API_KEY, model=GEMINI_TTS_MODEL)
    raise ValueError(f"Unknown VOICE_PROVIDER: {VOICE_PROVIDER}. Supported: 'gemini'")


class VoiceClient:
    """Provider-independent client for speech-to-text and text-to-speech."""

    def __init__(self):
        """Initialize the voice client with the configured provider."""
        self.stt_provider = _load_stt_provider()
        self.tts_provider = _load_tts_provider()

    def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        """Transcribe spoken audio into text.

        Raises:
            RuntimeError: If transcription fails
        """
        return self.stt_provider.transcribe(audio_bytes, mime_type)

    def synthesize(self, text: str) -> tuple[bytes, str]:
        """Synthesize spoken audio from text. Returns (audio_bytes, audio_mime_type).

        Raises:
            RuntimeError: If synthesis fails
        """
        return self.tts_provider.synthesize(text)
