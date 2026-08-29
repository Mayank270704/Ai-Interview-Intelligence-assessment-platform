"""LLM client - provider-independent interface for LLM operations."""

from typing import Type, TypeVar

from pydantic import BaseModel

from app.ai.llm.gemini_provider import GeminiProvider
from app.ai.llm.provider import LLMProvider
from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_PROVIDER

T = TypeVar("T", bound=BaseModel)


def _load_provider() -> LLMProvider:
    """
    Load the configured LLM provider.

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider is not configured or configuration is invalid
    """
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        return GeminiProvider(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {LLM_PROVIDER}. Supported: 'gemini'"
        )


class LLMClient:
    """Provider-independent LLM client."""

    def __init__(self):
        """Initialize the LLM client with the configured provider."""
        self.provider = _load_provider()

    def generate(self, prompt: str) -> str:
        """
        Generate text response from the LLM.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response

        Raises:
            RuntimeError: If generation fails
        """
        return self.provider.generate(prompt)

    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """
        Generate structured output from the LLM using a Pydantic model.

        Args:
            prompt: The input prompt
            response_model: Pydantic model class for the response

        Returns:
            Parsed response as instance of response_model

        Raises:
            RuntimeError: If generation fails
            ValueError: If response cannot be parsed to the model
        """
        return self.provider.generate_structured(prompt, response_model)