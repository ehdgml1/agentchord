"""AgentWeave RAG - Retrieval-Augmented Generation module.

Provides end-to-end RAG capabilities including:
    - Document loading (text, PDF, web)
    - Chunking (recursive, semantic, parent-child)
    - Embedding (OpenAI, Ollama, SentenceTransformer)
    - Vector storage (in-memory, ChromaDB, FAISS)
    - Search (BM25, hybrid with RRF)
    - Reranking (cross-encoder, LLM-based)
    - Pipeline orchestration
    - Agentic RAG tools
    - LLM-as-a-Judge evaluation
"""

from agentweave.rag.loaders import DirectoryLoader, DocumentLoader, TextLoader
from agentweave.rag.pipeline import RAGPipeline
from agentweave.rag.tools import create_rag_tools
from agentweave.rag.types import (
    Chunk,
    Document,
    RAGResponse,
    RetrievalResult,
    SearchResult,
)

__all__ = [
    # Pipeline
    "RAGPipeline",
    "create_rag_tools",
    # Loaders
    "DocumentLoader",
    "TextLoader",
    "DirectoryLoader",
    # Types
    "Document",
    "Chunk",
    "SearchResult",
    "RetrievalResult",
    "RAGResponse",
]
