"""Gemini LLM provider implementation."""

from typing import Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.ai.llm.provider import LLMProvider

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Gemini API provider implementation."""

    def __init__(self, api_key: str, model: str):
        """
        Initialize the Gemini provider.

        Args:
            api_key: Google Gemini API key
            model: Model identifier (e.g., 'gemini-2.0-flash')

        Raises:
            ValueError: If api_key or model is not provided
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if not model:
            raise ValueError("GEMINI_MODEL is required")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        """
        Generate text response from Gemini.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response

        Raises:
            RuntimeError: If Gemini API call fails
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {str(e)}")

    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """
        Generate structured output from Gemini using a Pydantic model.

        Args:
            prompt: The input prompt
            response_model: Pydantic model class for the response

        Returns:
            Parsed response as instance of response_model

        Raises:
            RuntimeError: If Gemini API call fails
            ValueError: If response cannot be parsed to the model
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_model,
                ),
            )

            response_text = response.text
            return response_model.model_validate_json(response_text)

        except ValueError as e:
            # Re-raise validation errors as-is
            raise ValueError(f"Failed to parse response as {response_model.__name__}: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Gemini structured generation failed: {str(e)}")
