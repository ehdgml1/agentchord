"""Parent-child chunking for precision with context."""
from __future__ import annotations

from agentweave.rag.chunking.base import Chunker
from agentweave.rag.chunking.recursive import RecursiveCharacterChunker
from agentweave.rag.types import Chunk, Document


class ParentChildChunker(Chunker):
    """Two-level chunking: small children for search, large parents for context.

    Children are indexed for precise search matching.
    Parents provide complete context for LLM generation.
    Solves the precision vs. context trade-off.
    """

    def __init__(
        self,
        parent_chunk_size: int = 1000,
        parent_overlap: int = 100,
        child_chunk_size: int = 200,
        child_overlap: int = 20,
    ) -> None:
        self._parent_chunker = RecursiveCharacterChunker(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_overlap,
        )
        self._child_chunker = RecursiveCharacterChunker(
            chunk_size=child_chunk_size,
            chunk_overlap=child_overlap,
        )

    def chunk(self, document: Document) -> list[Chunk]:
        parents = self._parent_chunker.chunk(document)

        all_chunks: list[Chunk] = []
        for parent in parents:
            parent.metadata = {**parent.metadata, "is_parent": True}
            all_chunks.append(parent)

            child_doc = Document(
                id=parent.id,
                content=parent.content,
                metadata=parent.metadata,
                source=document.source,
            )
            children = self._child_chunker.chunk(child_doc)
            for child in children:
                child.parent_id = parent.id
                child.document_id = document.id
                child.metadata = {**child.metadata, "is_parent": False}
                offset = parent.start_index
                child.start_index += offset
                child.end_index += offset
            all_chunks.extend(children)

        return all_chunks

    @staticmethod
    def get_parent(
        child: Chunk, all_chunks: list[Chunk]
    ) -> Chunk | None:
        if child.parent_id is None:
            return None
        for chunk in all_chunks:
            if chunk.id == child.parent_id:
                return chunk
        return None

    @staticmethod
    def get_children(
        parent: Chunk, all_chunks: list[Chunk]
    ) -> list[Chunk]:
        return [c for c in all_chunks if c.parent_id == parent.id]
