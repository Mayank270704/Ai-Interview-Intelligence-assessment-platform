"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass
