"""Embedding abstraction for World Knowledge retrieval."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-independent interface for generating embeddings."""

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        """Return a numeric embedding for the given text."""


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embedding implementation for tests and lightweight usage."""

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    def generate_embedding(self, text: str) -> list[float]:
        """Generate a deterministic hash-based vector without external dependencies."""
        values: list[float] = []
        for index in range(self.dimensions):
            seed = f"{text.lower()}::{index}".encode("utf-8")
            digest = hashlib.sha256(seed).hexdigest()
            value = int(digest[:8], 16) / float(0xFFFFFFFF)
            values.append(value)
        return values
