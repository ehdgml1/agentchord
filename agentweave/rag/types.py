"""Core types for the RAG module."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Document(BaseModel):
    """A source document before chunking."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Chunk(BaseModel):
    """A chunk of a document after splitting."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    document_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    start_index: int = 0
    end_index: int = 0
    embedding: list[float] | None = None
    parent_id: str | None = None


class SearchResult(BaseModel):
    """A single search result with score."""

    chunk: Chunk
    score: float
    source: str = "vector"


class RetrievalResult(BaseModel):
    """Complete retrieval result from a RAG query."""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    total_ms: float = 0.0

    @property
    def contexts(self) -> list[str]:
        """Get context strings for LLM prompt."""
        return [r.chunk.content for r in self.results]

    @property
    def context_string(self) -> str:
        """Get concatenated context for LLM prompt."""
        return "\n\n---\n\n".join(self.contexts)


class RAGResponse(BaseModel):
    """Complete RAG response including retrieval and generation."""

    query: str
    answer: str
    retrieval: RetrievalResult
    usage: dict[str, int] = Field(default_factory=dict)
    source_documents: list[str] = Field(default_factory=list)
