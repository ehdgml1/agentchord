"""In-memory vector store for development and testing."""
from __future__ import annotations

from typing import Any

from agentchord.rag.types import Chunk, SearchResult
from agentchord.rag.vectorstore.base import VectorStore
from agentchord.utils.math import cosine_similarity


class InMemoryVectorStore(VectorStore):
    """In-memory vector store using brute-force cosine similarity.

    No external dependencies. Suitable for up to ~10,000 vectors.
    Data is not persisted across restarts.
    """

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._dimensions: int | None = None

    async def add(self, chunks: list[Chunk]) -> list[str]:
        ids: list[str] = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")
            dim = len(chunk.embedding)
            if self._dimensions is None:
                self._dimensions = dim
            elif dim != self._dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self._dimensions}, got {dim} "
                    f"for chunk {chunk.id}"
                )
            self._chunks[chunk.id] = chunk
            self._embeddings[chunk.id] = chunk.embedding
            ids.append(chunk.id)
        return ids

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if not self._chunks:
            return []

        scores: list[tuple[str, float]] = []
        for chunk_id, embedding in self._embeddings.items():
            if filter:
                chunk = self._chunks[chunk_id]
                if not self._matches_filter(chunk, filter):
                    continue
            similarity = cosine_similarity(query_embedding, embedding)
            scores.append((chunk_id, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                chunk=self._chunks[chunk_id],
                score=max(0.0, score),
                source="vector",
            )
            for chunk_id, score in scores[:limit]
        ]

    async def delete(self, chunk_ids: list[str]) -> int:
        deleted = 0
        for chunk_id in chunk_ids:
            if chunk_id in self._chunks:
                del self._chunks[chunk_id]
                del self._embeddings[chunk_id]
                deleted += 1
        return deleted

    async def clear(self) -> None:
        self._chunks.clear()
        self._embeddings.clear()
        self._dimensions = None

    async def count(self) -> int:
        return len(self._chunks)

    async def get(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)

    @staticmethod
    def _matches_filter(chunk: Chunk, filter: dict[str, Any]) -> bool:
        for key, value in filter.items():
            if chunk.metadata.get(key) != value:
                return False
        return True
