"""ChromaDB-backed vector store."""
from __future__ import annotations

import asyncio
from typing import Any

from agentchord.rag.types import Chunk, SearchResult
from agentchord.rag.vectorstore.base import VectorStore


class ChromaVectorStore(VectorStore):
    """ChromaDB-backed vector store.

    Requires: pip install chromadb
    Supports persistent storage and metadata filtering.
    """

    def __init__(
        self,
        collection_name: str = "agentchord",
        persist_directory: str | None = None,
    ) -> None:
        self._collection_name = collection_name
        self._persist_directory = persist_directory
        self._client: Any = None
        self._collection: Any = None

    def _get_collection(self) -> Any:
        if self._collection is None:
            try:
                import chromadb
            except ImportError as e:
                raise ImportError(
                    "chromadb is required for ChromaVectorStore. "
                    "Install with: pip install chromadb"
                ) from e
            if self._persist_directory:
                self._client = chromadb.PersistentClient(
                    path=self._persist_directory
                )
            else:
                self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add(self, chunks: list[Chunk]) -> list[str]:
        if not chunks:
            return []
        collection = self._get_collection()
        ids = [c.id for c in chunks]
        embeddings = []
        documents = []
        metadatas = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")
            embeddings.append(chunk.embedding)
            documents.append(chunk.content)
            meta = dict(chunk.metadata) if chunk.metadata else {}
            meta["_document_id"] = chunk.document_id or ""
            meta["_start_index"] = chunk.start_index
            meta["_end_index"] = chunk.end_index
            meta["_parent_id"] = chunk.parent_id or ""
            metadatas.append(meta)

        await asyncio.to_thread(
            collection.upsert,
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return ids

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        collection = self._get_collection()
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": limit,
        }
        if filter:
            kwargs["where"] = filter

        raw = await asyncio.to_thread(collection.query, **kwargs)

        results: list[SearchResult] = []
        if raw["ids"] and raw["ids"][0]:
            for i, chunk_id in enumerate(raw["ids"][0]):
                distance = raw["distances"][0][i] if raw.get("distances") else 0.0
                score = max(0.0, 1.0 - distance)
                content = raw["documents"][0][i] if raw.get("documents") else ""
                metadata = raw["metadatas"][0][i] if raw.get("metadatas") else {}
                results.append(
                    SearchResult(
                        chunk=Chunk(
                            id=chunk_id,
                            content=content,
                            metadata={
                                k: v for k, v in metadata.items() if not k.startswith("_")
                            },
                            document_id=metadata.get("_document_id", ""),
                            start_index=metadata.get("_start_index", 0),
                            end_index=metadata.get("_end_index", 0),
                            parent_id=metadata.get("_parent_id") or None,
                        ),
                        score=score,
                        source="vector",
                    )
                )
        return results

    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by IDs.

        Note: Returns len(chunk_ids) as ChromaDB does not report actual
        deletion count. IDs that don't exist are silently ignored.
        """
        collection = self._get_collection()
        await asyncio.to_thread(collection.delete, ids=chunk_ids)
        return len(chunk_ids)

    async def clear(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(
                self._client.delete_collection, self._collection_name
            )
            self._collection = None
            self._get_collection()

    async def count(self) -> int:
        collection = self._get_collection()
        return await asyncio.to_thread(collection.count)

    async def get(self, chunk_id: str) -> Chunk | None:
        collection = self._get_collection()
        raw = await asyncio.to_thread(collection.get, ids=[chunk_id])
        if not raw["ids"] or not raw["ids"][0]:
            return None
        content = raw["documents"][0] if raw.get("documents") else ""
        metadata = raw["metadatas"][0] if raw.get("metadatas") else {}
        return Chunk(
            id=chunk_id,
            content=content,
            metadata={k: v for k, v in metadata.items() if not k.startswith("_")},
            document_id=metadata.get("_document_id", ""),
            start_index=metadata.get("_start_index", 0),
            end_index=metadata.get("_end_index", 0),
            parent_id=metadata.get("_parent_id") or None,
        )
