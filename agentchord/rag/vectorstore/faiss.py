"""FAISS-backed vector store for high-performance search."""
from __future__ import annotations

import asyncio
from typing import Any

from agentchord.rag.types import Chunk, SearchResult
from agentchord.rag.vectorstore.base import VectorStore


class FAISSVectorStore(VectorStore):
    """FAISS-backed vector store.

    Requires: pip install faiss-cpu (or faiss-gpu)
    Provides GPU-accelerated similarity search.
    """

    def __init__(self, dimensions: int, index_type: str = "flat") -> None:
        """Initialize FAISS vector store.

        Args:
            dimensions: Vector dimension size.
            index_type: FAISS index type ('flat' for exact search).
        """
        try:
            import faiss
            import numpy as np
        except ImportError as e:
            raise ImportError(
                "faiss-cpu and numpy are required for FAISSVectorStore. "
                "Install with: pip install faiss-cpu numpy"
            ) from e

        self._dimensions = dimensions
        if index_type == "flat":
            self._index = faiss.IndexFlatIP(dimensions)
        else:
            raise ValueError(f"Unsupported index_type: {index_type!r}. Currently only 'flat' is supported.")

        self._chunks: dict[int, Chunk] = {}
        self._id_map: dict[str, int] = {}
        self._deleted_ids: set[int] = set()
        self._next_idx: int = 0

    async def add(self, chunks: list[Chunk]) -> list[str]:
        import numpy as np

        if not chunks:
            return []

        vectors = []
        ids: list[str] = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")
            if len(chunk.embedding) != self._dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self._dimensions}, "
                    f"got {len(chunk.embedding)} for chunk {chunk.id}"
                )
            vectors.append(chunk.embedding)
            self._chunks[self._next_idx] = chunk
            self._id_map[chunk.id] = self._next_idx
            ids.append(chunk.id)
            self._next_idx += 1

        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        arr = arr / norms

        await asyncio.to_thread(self._index.add, arr)
        return ids

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        import numpy as np

        if self._index.ntotal == 0:
            return []

        query = np.array([query_embedding], dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        search_limit = min(limit * 3, self._index.ntotal) if filter else limit
        scores_arr, indices = await asyncio.to_thread(
            self._index.search, query, search_limit
        )

        results: list[SearchResult] = []
        for score, idx in zip(scores_arr[0], indices[0]):
            if idx < 0:
                continue
            if int(idx) in self._deleted_ids:
                continue
            chunk = self._chunks.get(int(idx))
            if chunk is None:
                continue
            if filter and not self._matches_filter(chunk, filter):
                continue
            results.append(
                SearchResult(
                    chunk=chunk,
                    score=max(0.0, float(score)),
                    source="vector",
                )
            )
            if len(results) >= limit:
                break

        return results

    async def delete(self, chunk_ids: list[str]) -> int:
        deleted = 0
        for chunk_id in chunk_ids:
            idx = self._id_map.pop(chunk_id, None)
            if idx is not None:
                self._chunks.pop(idx, None)
                self._deleted_ids.add(idx)
                deleted += 1
        return deleted

    async def clear(self) -> None:
        self._index.reset()
        self._chunks.clear()
        self._id_map.clear()
        self._deleted_ids.clear()
        self._next_idx = 0

    async def count(self) -> int:
        return self._index.ntotal - len(self._deleted_ids)

    async def get(self, chunk_id: str) -> Chunk | None:
        idx = self._id_map.get(chunk_id)
        if idx is None:
            return None
        return self._chunks.get(idx)

    @staticmethod
    def _matches_filter(chunk: Chunk, filter: dict[str, Any]) -> bool:
        for key, value in filter.items():
            if chunk.metadata.get(key) != value:
                return False
        return True
