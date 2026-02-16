"""Base embedding provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers.

    All providers must support both single and batch embedding.
    Batch embedding is preferred for efficiency.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the embedding model name."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Get the embedding vector dimension size."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.
        """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single operation.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors in same order as input.
        """
