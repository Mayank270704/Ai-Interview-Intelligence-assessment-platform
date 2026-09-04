"""Gemini LLM provider implementation."""

import logging
import time
from functools import lru_cache
from typing import Type, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.ai.llm.provider import LLMProvider
from app.core.config import GEMINI_THINKING_LEVEL, GEMINI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Gemini answers these with a retryable status: the request was never processed,
# so re-sending it is safe and is usually all that is needed.
TRANSIENT_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0


class LLMUnavailableError(RuntimeError):
    """The model could not be reached, or refused the request temporarily.

    Distinct from a malformed or unparseable response, so a caller can tell an
    upstream outage apart from a bug in its own prompt or schema.
    """


@lru_cache(maxsize=4)
def shared_client(api_key: str) -> genai.Client:
    """One client per API key, reused across providers.

    Constructing a genai.Client costs roughly half a second, and the interview
    pipeline builds several provider instances per request (question engine,
    answer analysis, reasoning engine, voice). The client itself is stateless
    per request, so sharing it removes that cost without changing behaviour.
    """
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(GEMINI_TIMEOUT_SECONDS * 1000)),
    )


def base_config_fields(*, thinking: bool = True) -> dict:
    """Config the calls share: no tool calling, and bounded reasoning effort.

    `thinking=False` is for calls whose output must be exactly what the model
    was asked to produce and nothing else -- verbatim transcription, notably,
    where a reasoning preamble ends up inside the transcript itself.
    """
    fields: dict = {
        # No tool is ever passed, so automatic function calling has nothing to
        # do here; declaring that keeps the SDK from arming (and warning about)
        # a call loop this application does not use.
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
    }
    if thinking and GEMINI_THINKING_LEVEL:
        fields["thinking_config"] = types.ThinkingConfig(
            thinking_level=GEMINI_THINKING_LEVEL
        )
    return fields


def call_with_retry(operation, description: str):
    """Run one Gemini call, retrying only statuses that mean 'not processed yet'."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return operation()
        except genai_errors.APIError as exc:
            if exc.code not in TRANSIENT_STATUS_CODES or attempt == MAX_ATTEMPTS:
                raise
            last_error = exc
            delay = RETRY_BACKOFF_SECONDS * attempt
            logger.warning(
                "%s failed with retryable status %s (attempt %s/%s); retrying in %ss",
                description,
                exc.code,
                attempt,
                MAX_ATTEMPTS,
                delay,
            )
            time.sleep(delay)
    raise last_error  # pragma: no cover - loop always returns or raises above


class GeminiProvider(LLMProvider):
    """Gemini API provider implementation."""

    def __init__(self, api_key: str, model: str):
        """
        Initialize the Gemini provider.

        Args:
            api_key: Google Gemini API key
            model: Model identifier (e.g., 'gemini-3.6-flash')

        Raises:
            ValueError: If api_key or model is not provided
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if not model:
            raise ValueError("GEMINI_MODEL is required")

        self.client = shared_client(api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        """
        Generate text response from Gemini.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response

        Raises:
            LLMUnavailableError: If the Gemini API call fails
        """
        try:
            response = call_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**base_config_fields()),
                ),
                "Gemini generation",
            )
            return response.text
        except Exception as e:
            raise LLMUnavailableError(f"Gemini generation failed: {str(e)}")

    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """
        Generate structured output from Gemini using a Pydantic model.

        Args:
            prompt: The input prompt
            response_model: Pydantic model class for the response

        Returns:
            Parsed response as instance of response_model

        Raises:
            LLMUnavailableError: If the Gemini API call fails
            ValueError: If response cannot be parsed to the model
        """
        try:
            response = call_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_model,
                        **base_config_fields(),
                    ),
                ),
                f"Gemini structured generation ({response_model.__name__})",
            )
        except Exception as e:
            raise LLMUnavailableError(f"Gemini structured generation failed: {str(e)}")

        # A response truncated by an output-token limit or stopped by a safety
        # filter carries no text; that is an empty answer, not a parse failure.
        response_text = response.text
        if not response_text:
            raise LLMUnavailableError(
                f"Gemini returned no content for {response_model.__name__} "
                f"(finish reason: {_finish_reason(response)})"
            )

        try:
            return response_model.model_validate_json(response_text)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse response as {response_model.__name__}: {str(e)}"
            )


def _finish_reason(response) -> str:
    """Why the model stopped, for logs and error detail. Never includes content."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return "no candidates"
    return str(getattr(candidates[0], "finish_reason", "unknown"))
