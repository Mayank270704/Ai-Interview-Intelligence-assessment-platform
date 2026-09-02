"""Abstract speech-to-text and text-to-speech provider interfaces."""

from abc import ABC, abstractmethod


class SpeechToTextProvider(ABC):
    """Abstract interface for speech-to-text providers."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        """
        Transcribe spoken audio into text.

        Args:
            audio_bytes: Raw audio file bytes
            mime_type: MIME type of the audio (e.g. 'audio/wav')

        Returns:
            The transcribed text

        Raises:
            RuntimeError: If transcription fails
        """


class TextToSpeechProvider(ABC):
    """Abstract interface for text-to-speech providers."""

    @abstractmethod
    def synthesize(self, text: str) -> tuple[bytes, str]:
        """
        Synthesize spoken audio from text.

        Args:
            text: The text to speak

        Returns:
            A tuple of (audio_bytes, audio_mime_type)

        Raises:
            RuntimeError: If synthesis fails
        """
