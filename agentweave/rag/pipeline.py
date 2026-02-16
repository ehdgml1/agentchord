"""End-to-end RAG pipeline.

Orchestrates the full RAG workflow:
    1. Ingest: Load → Chunk → Embed → Store
    2. Retrieve: Query → Search → Rerank
    3. Generate: Context + Query → LLM → Answer

The pipeline provides both the full query() flow and individual
step access for custom pipelines.

Example:
    pipeline = RAGPipeline(
        llm=OpenAIProvider(model="gpt-4o-mini"),
        embedding_provider=OpenAIEmbeddings(),
    )
    await pipeline.ingest([TextLoader("data/docs.txt")])
    response = await pipeline.query("What is AgentWeave?")
    print(response.answer)
"""

from __future__ import annotations

from typing import Any

from agentweave.core.types import Message, MessageRole
from agentweave.llm.base import BaseLLMProvider
from agentweave.rag.chunking.base import Chunker
from agentweave.rag.chunking.recursive import RecursiveCharacterChunker
from agentweave.rag.embeddings.base import EmbeddingProvider
from agentweave.rag.loaders.base import DocumentLoader
from agentweave.rag.search.bm25 import BM25Search
from agentweave.rag.search.hybrid import HybridSearch
from agentweave.rag.search.reranker import Reranker
from agentweave.rag.types import Document, RAGResponse, RetrievalResult
from agentweave.rag.vectorstore.base import VectorStore
from agentweave.rag.vectorstore.in_memory import InMemoryVectorStore


_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based on "
    "the provided context. If the context doesn't contain enough information "
    "to answer, say so clearly. Do not make up information.\n\n"
    "Context:\n{context}"
)


class RAGPipeline:
    """End-to-end RAG pipeline for ingest, retrieve, and generate.

    Provides a high-level API for the complete RAG workflow.
    Each step can also be called individually for custom flows.
    """

    def __init__(
        self,
        llm: BaseLLMProvider,
        embedding_provider: EmbeddingProvider,
        *,
        vectorstore: VectorStore | None = None,
        chunker: Chunker | None = None,
        reranker: Reranker | None = None,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
        search_limit: int = 5,
        enable_bm25: bool = True,
    ) -> None:
        """Initialize RAG pipeline.

        Args:
            llm: LLM provider for answer generation.
            embedding_provider: Embedding provider for vectorization.
            vectorstore: Vector store backend. Defaults to InMemoryVectorStore.
            chunker: Document chunker. Defaults to RecursiveCharacterChunker.
            reranker: Optional reranker for improved precision.
            system_prompt: System prompt template. Use {context} placeholder.
            search_limit: Number of search results to use as context.
            enable_bm25: Whether to use hybrid search with BM25.
        """
        self._llm = llm
        self._embedding = embedding_provider
        self._vectorstore = vectorstore or InMemoryVectorStore()
        self._chunker = chunker or RecursiveCharacterChunker()
        self._reranker = reranker
        self._system_prompt = system_prompt
        self._search_limit = search_limit

        bm25 = BM25Search() if enable_bm25 else None
        self._search = HybridSearch(
            vectorstore=self._vectorstore,
            embedding_provider=self._embedding,
            bm25=bm25,
            reranker=self._reranker,
        )
        self._ingested_count: int = 0
        self._closed: bool = False

    @property
    def ingested_count(self) -> int:
        """Number of chunks ingested."""
        return self._ingested_count

    async def ingest(self, loaders: list[DocumentLoader]) -> int:
        """Ingest documents from loaders.

        Pipeline: Load → Chunk → Embed → Store

        Args:
            loaders: Document loaders to ingest from.

        Returns:
            Number of chunks ingested.
        """
        # 1. Load documents from all loaders
        documents: list[Document] = []
        for loader in loaders:
            docs = await loader.load()
            documents.extend(docs)

        return await self.ingest_documents(documents)

    async def ingest_documents(self, documents: list[Document]) -> int:
        """Ingest pre-loaded documents.

        Args:
            documents: Documents to chunk, embed, and store.

        Returns:
            Number of chunks ingested.
        """
        if not documents:
            return 0

        # 1. Chunk
        chunks = self._chunker.chunk_many(documents)

        # 2. Embed
        texts = [c.content for c in chunks]
        embeddings = await self._embedding.embed_batch(texts)
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        # 3. Store (add to hybrid search which handles both vectorstore + BM25)
        await self._search.add(chunks)
        self._ingested_count += len(chunks)
        return len(chunks)

    async def retrieve(
        self,
        query: str,
        limit: int | None = None,
        *,
        filter: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant context for a query.

        Args:
            query: Search query.
            limit: Override default search limit.
            filter: Optional metadata filter.

        Returns:
            RetrievalResult with search results and timing.
        """
        return await self._search.search(
            query,
            limit=limit or self._search_limit,
            filter=filter,
        )

    async def generate(
        self,
        query: str,
        retrieval: RetrievalResult,
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> RAGResponse:
        """Generate answer from query and retrieved context.

        Args:
            query: User's question.
            retrieval: Retrieved context from search.
            temperature: LLM temperature.
            max_tokens: Maximum response tokens.

        Returns:
            RAGResponse with answer and source info.
        """
        context = retrieval.context_string
        system_content = self._system_prompt.replace("{context}", context)

        messages = [
            Message(role=MessageRole.SYSTEM, content=system_content),
            Message(role=MessageRole.USER, content=query),
        ]

        try:
            response = await self._llm.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            answer = response.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        except Exception as e:
            answer = f"Failed to generate answer: {e}"
            usage = {}

        return RAGResponse(
            query=query,
            answer=answer,
            retrieval=retrieval,
            usage=usage,
            source_documents=list({
                r.chunk.document_id
                for r in retrieval.results
                if r.chunk.document_id
            }),
        )

    async def query(
        self,
        question: str,
        *,
        limit: int | None = None,
        filter: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> RAGResponse:
        """Full RAG query: Retrieve → Generate.

        Convenience method combining retrieve() and generate().

        Args:
            question: User's question.
            limit: Number of search results.
            filter: Optional metadata filter.
            temperature: LLM temperature.
            max_tokens: Maximum response tokens.

        Returns:
            Complete RAGResponse.
        """
        retrieval = await self.retrieve(question, limit=limit, filter=filter)
        return await self.generate(
            question,
            retrieval,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def clear(self) -> None:
        """Clear all ingested data."""
        await self._search.clear()
        self._ingested_count = 0

    async def close(self) -> None:
        """Release pipeline resources.

        Clears stored data and resets internal state.
        Safe to call multiple times (idempotent).
        """
        if getattr(self, "_closed", False):
            return
        self._closed = True
        await self.clear()

    async def __aenter__(self) -> "RAGPipeline":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
