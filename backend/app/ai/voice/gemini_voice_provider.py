"""Gemini speech-to-text and text-to-speech provider implementations."""

from google import genai
from google.genai import types

from app.ai.voice.provider import SpeechToTextProvider, TextToSpeechProvider

_DEFAULT_VOICE = "Kore"
_TRANSCRIBE_INSTRUCTION = (
    "Transcribe this audio verbatim. Return only the spoken words, with no "
    "commentary, labels, or formatting."
)


class GeminiSpeechToTextProvider(SpeechToTextProvider):
    """Speech-to-text via Gemini's multimodal audio understanding."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if not model:
            raise ValueError("GEMINI_MODEL is required")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    _TRANSCRIBE_INSTRUCTION,
                ],
            )
            transcript = (response.text or "").strip()
        except Exception as exc:
            raise RuntimeError(f"Gemini transcription failed: {exc}") from exc

        if not transcript:
            raise RuntimeError("Gemini transcription returned no text")
        return transcript


class GeminiTextToSpeechProvider(TextToSpeechProvider):
    """Text-to-speech via Gemini's audio-output models."""

    def __init__(self, api_key: str, model: str, voice: str = _DEFAULT_VOICE):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if not model:
            raise ValueError("GEMINI_TTS_MODEL is required")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.voice = voice

    def synthesize(self, text: str) -> tuple[bytes, str]:
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice
                            )
                        )
                    ),
                ),
            )
            part = response.candidates[0].content.parts[0]
            audio_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "audio/pcm"
        except Exception as exc:
            raise RuntimeError(f"Gemini speech synthesis failed: {exc}") from exc

        if not audio_bytes:
            raise RuntimeError("Gemini speech synthesis returned no audio")
        return audio_bytes, mime_type
