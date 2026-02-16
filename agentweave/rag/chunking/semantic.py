"""Semantic chunking based on embedding similarity."""
from __future__ import annotations

import asyncio
import re
from typing import Any

from agentweave.rag.chunking.base import Chunker
from agentweave.rag.types import Chunk, Document
from agentweave.utils.math import cosine_similarity

_SENTENCE_PATTERN = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\s*(?=\S)'
)


class SemanticChunker(Chunker):
    """Split text based on semantic similarity between sentences.

    Embeds each sentence and splits where cosine similarity
    between adjacent sentences drops below threshold.

    More expensive than recursive chunking but preserves topic coherence.
    """

    def __init__(
        self,
        embedding_provider: Any,
        threshold: float = 0.5,
        min_chunk_size: int = 100,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self._embedding_provider = embedding_provider
        self._threshold = threshold
        self._min_chunk_size = min_chunk_size

    def chunk(self, document: Document) -> list[Chunk]:
        """Split document into semantically coherent chunks.

        Note: This method bridges sync->async for the embedding calls.
        When called from an async context, prefer chunk_async() directly.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Already in async context — use a new thread to avoid blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self._chunk_async(document))
                return future.result()
        else:
            return asyncio.run(self._chunk_async(document))

    async def chunk_async(self, document: Document) -> list[Chunk]:
        """Async version of chunk() — preferred when in async context."""
        return await self._chunk_async(document)

    async def _chunk_async(self, document: Document) -> list[Chunk]:
        sentences = self._split_sentences(document.content)
        if len(sentences) <= 1:
            return [
                Chunk(
                    content=document.content,
                    document_id=document.id,
                    metadata={**document.metadata, "source": document.source},
                    start_index=0,
                    end_index=len(document.content),
                )
            ] if document.content.strip() else []

        embeddings = await self._embedding_provider.embed_batch(sentences)

        groups: list[list[str]] = [[sentences[0]]]
        for i in range(1, len(sentences)):
            sim = cosine_similarity(embeddings[i - 1], embeddings[i])
            if sim < self._threshold:
                groups.append([sentences[i]])
            else:
                groups[-1].append(sentences[i])

        merged_groups = self._merge_small_groups(groups)

        chunks: list[Chunk] = []
        offset = 0
        for group in merged_groups:
            content = " ".join(group)
            start = document.content.find(group[0], offset)
            if start == -1:
                start = offset
            chunks.append(
                Chunk(
                    content=content,
                    document_id=document.id,
                    metadata={**document.metadata, "source": document.source},
                    start_index=start,
                    end_index=start + len(content),
                )
            )
            offset = start + len(group[0])

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        parts = _SENTENCE_PATTERN.split(text)
        return [p.strip() for p in parts if p.strip()]

    def _merge_small_groups(
        self, groups: list[list[str]]
    ) -> list[list[str]]:
        merged: list[list[str]] = []
        for group in groups:
            content = " ".join(group)
            if merged and len(content) < self._min_chunk_size:
                merged[-1].extend(group)
            else:
                merged.append(group)
        return merged
