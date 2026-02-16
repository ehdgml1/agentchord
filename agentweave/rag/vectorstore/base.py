"""Abstract vector store interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentweave.rag.types import Chunk, SearchResult


class VectorStore(ABC):
    """Abstract base for vector storage backends.

    Supports CRUD operations on chunks with embeddings
    and similarity search with optional metadata filtering.
    """

    @abstractmethod
    async def add(self, chunks: list[Chunk]) -> list[str]:
        """Add chunks with embeddings to the store.

        Args:
            chunks: Chunks with embedding field populated.

        Returns:
            List of stored chunk IDs.

        Raises:
            ValueError: If any chunk has no embedding.
        """

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_embedding: Query vector.
            limit: Maximum number of results.
            filter: Optional metadata filter (key-value equality).

        Returns:
            SearchResults sorted by score descending.
        """

    @abstractmethod
    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by ID.

        Args:
            chunk_ids: IDs of chunks to delete.

        Returns:
            Number of chunks deleted.
        """

    @abstractmethod
    async def clear(self) -> None:
        """Clear all stored vectors."""

    @abstractmethod
    async def count(self) -> int:
        """Get total number of stored vectors."""

    async def get(self, chunk_id: str) -> Chunk | None:
        """Get a chunk by ID.

        Default implementation returns None. Override for efficiency.
        """
        return None
