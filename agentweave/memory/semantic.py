"""Semantic memory implementation."""

from __future__ import annotations

from typing import Callable

from agentweave.memory.base import BaseMemory, MemoryEntry
from agentweave.utils.math import cosine_similarity as _cosine_similarity


# Type alias for embedding function
EmbeddingFunc = Callable[[str], list[float]]


class SemanticMemory(BaseMemory):
    """Semantic memory with vector similarity search.

    Uses embeddings to find semantically similar entries.
    Requires an embedding function to convert text to vectors.

    Example:
        >>> def embed(text: str) -> list[float]:
        ...     # Use OpenAI, sentence-transformers, etc.
        ...     return openai.embeddings.create(input=text, model="text-embedding-3-small").data[0].embedding
        >>> memory = SemanticMemory(embedding_func=embed)
        >>> memory.add(MemoryEntry(content="The capital of France is Paris"))
        >>> results = memory.search("French cities", limit=3)
    """

    def __init__(
        self,
        embedding_func: EmbeddingFunc,
        similarity_threshold: float = 0.5,
    ) -> None:
        """Initialize semantic memory.

        Args:
            embedding_func: Function to convert text to embedding vector.
            similarity_threshold: Minimum similarity score for search results (0-1).
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")

        self._embedding_func = embedding_func
        self._similarity_threshold = similarity_threshold
        self._entries: dict[str, MemoryEntry] = {}
        self._embeddings: dict[str, list[float]] = {}

    @property
    def similarity_threshold(self) -> float:
        """Minimum similarity threshold for search."""
        return self._similarity_threshold

    def add(self, entry: MemoryEntry) -> None:
        """Add entry with computed embedding."""
        self._entries[entry.id] = entry
        self._embeddings[entry.id] = self._embedding_func(entry.content)

    def add_with_embedding(
        self,
        entry: MemoryEntry,
        embedding: list[float],
    ) -> None:
        """Add entry with pre-computed embedding.

        Use this when you already have the embedding to avoid recomputation.
        """
        self._entries[entry.id] = entry
        self._embeddings[entry.id] = embedding

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Get entry by ID."""
        return self._entries.get(entry_id)

    def get_embedding(self, entry_id: str) -> list[float] | None:
        """Get embedding for an entry."""
        return self._embeddings.get(entry_id)

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get most recent entries by timestamp."""
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return sorted_entries[:limit]

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Search for semantically similar entries.

        Args:
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            List of entries sorted by similarity (most similar first).
        """
        if not self._entries:
            return []

        query_embedding = self._embedding_func(query)
        return self.search_by_embedding(query_embedding, limit)

    def search_by_embedding(
        self,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Search using pre-computed query embedding."""
        if not self._entries:
            return []

        # Calculate similarity scores
        scores: list[tuple[str, float]] = []
        for entry_id, embedding in self._embeddings.items():
            similarity = _cosine_similarity(query_embedding, embedding)
            if similarity >= self._similarity_threshold:
                scores.append((entry_id, similarity))

        # Sort by similarity descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top entries
        return [
            self._entries[entry_id]
            for entry_id, _ in scores[:limit]
        ]

    def clear(self) -> None:
        """Clear all entries and embeddings."""
        self._entries.clear()
        self._embeddings.clear()

    def remove(self, entry_id: str) -> bool:
        """Remove entry by ID.

        Returns:
            True if entry was found and removed, False otherwise.
        """
        if entry_id in self._entries:
            del self._entries[entry_id]
            del self._embeddings[entry_id]
            return True
        return False

    def __len__(self) -> int:
        """Return number of entries."""
        return len(self._entries)
