"""Document chunking interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from agentweave.rag.types import Chunk, Document


class Chunker(ABC):
    """Abstract base for document chunking strategies."""

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Split a document into chunks.

        Args:
            document: Source document to split.

        Returns:
            List of chunks with document_id and position info set.
        """

    def chunk_many(self, documents: list[Document]) -> list[Chunk]:
        """Chunk multiple documents.

        Args:
            documents: Source documents.

        Returns:
            All chunks from all documents, in document order.
        """
        chunks: list[Chunk] = []
        for doc in documents:
            chunks.extend(self.chunk(doc))
        return chunks
