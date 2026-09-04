"""Gemini speech-to-text and text-to-speech provider implementations."""

from google.genai import types

from app.ai.llm.gemini_provider import (
    LLMUnavailableError,
    base_config_fields,
    call_with_retry,
    shared_client,
)
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

        self.client = shared_client(api_key)
        self.model = model

    def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        try:
            response = call_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        _TRANSCRIBE_INSTRUCTION,
                    ],
                    # Transcription must return the spoken words and nothing
                    # else, so this call carries no reasoning budget: with one,
                    # the model prefixes its own preamble to the transcript.
                    config=types.GenerateContentConfig(
                        **base_config_fields(thinking=False)
                    ),
                ),
                "Gemini transcription",
            )
            transcript = (response.text or "").strip()
        except Exception as exc:
            raise LLMUnavailableError(f"Gemini transcription failed: {exc}") from exc

        if not transcript:
            raise LLMUnavailableError("Gemini transcription returned no text")
        return transcript


class GeminiTextToSpeechProvider(TextToSpeechProvider):
    """Text-to-speech via Gemini's audio-output models."""

    def __init__(self, api_key: str, model: str, voice: str = _DEFAULT_VOICE):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if not model:
            raise ValueError("GEMINI_TTS_MODEL is required")

        self.client = shared_client(api_key)
        self.model = model
        self.voice = voice

    def synthesize(self, text: str) -> tuple[bytes, str]:
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")

        try:
            response = call_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=text,
                    # The audio-output models take neither a thinking budget nor
                    # tools, so this call carries only its speech configuration.
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
                ),
                "Gemini speech synthesis",
            )
            part = response.candidates[0].content.parts[0]
            audio_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "audio/pcm"
        except Exception as exc:
            raise LLMUnavailableError(f"Gemini speech synthesis failed: {exc}") from exc

        if not audio_bytes:
            raise LLMUnavailableError("Gemini speech synthesis returned no audio")
        return audio_bytes, mime_type
