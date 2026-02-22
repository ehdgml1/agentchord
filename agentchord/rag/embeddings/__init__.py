"""Embedding providers for RAG."""

from agentchord.rag.embeddings.base import EmbeddingProvider
from agentchord.rag.embeddings.gemini import GeminiEmbeddings

__all__ = ["EmbeddingProvider", "GeminiEmbeddings"]
