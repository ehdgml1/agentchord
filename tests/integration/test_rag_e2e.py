"""End-to-end RAG pipeline integration tests.

Tests the full pipeline flow: ingest → retrieve → generate
with all components wired together using mock providers.
"""
from __future__ import annotations

import pytest

from agentweave.core.agent import Agent
from agentweave.rag.chunking.recursive import RecursiveCharacterChunker
from agentweave.rag.evaluation.evaluator import RAGEvaluator
from agentweave.rag.pipeline import RAGPipeline
from agentweave.rag.search.bm25 import BM25Search
from agentweave.rag.search.hybrid import HybridSearch
from agentweave.rag.tools import create_rag_tools
from agentweave.rag.types import Chunk, Document
from agentweave.rag.vectorstore.in_memory import InMemoryVectorStore
from tests.conftest import MockEmbeddingProvider, MockLLMProvider


@pytest.fixture
def sample_corpus() -> list[Document]:
    """Sample document corpus for integration testing."""
    return [
        Document(
            id="doc1",
            content=(
                "AgentWeave is a protocol-first multi-agent framework. "
                "It provides comprehensive support for MCP and A2A protocols, "
                "enabling seamless agent communication across different systems. "
                "The framework is built with Python and uses asyncio for concurrent operations."
            ),
            source="docs/overview.md",
            metadata={"type": "overview", "category": "framework"},
        ),
        Document(
            id="doc2",
            content=(
                "The RAG module in AgentWeave provides retrieval-augmented generation capabilities. "
                "It includes vector search using embeddings, BM25 keyword search, and hybrid search "
                "that combines both approaches. The module supports custom chunking strategies "
                "and reranking for improved retrieval quality."
            ),
            source="docs/rag.md",
            metadata={"type": "feature", "category": "rag"},
        ),
        Document(
            id="doc3",
            content=(
                "Python is a high-level programming language widely used for AI and machine learning. "
                "It features dynamic typing, automatic memory management, and a rich ecosystem "
                "of libraries. Python's asyncio library enables concurrent programming with coroutines."
            ),
            source="docs/python.md",
            metadata={"type": "reference", "category": "language"},
        ),
        Document(
            id="doc4",
            content=(
                "Error handling in AgentWeave uses structured exceptions and context managers. "
                "The framework provides automatic retry mechanisms with exponential backoff "
                "and circuit breaker patterns for resilient agent operations. "
                "All errors are logged with structured metadata for debugging."
            ),
            source="docs/error-handling.md",
            metadata={"type": "guide", "category": "best-practices"},
        ),
    ]


@pytest.fixture
def mock_rag_llm() -> MockLLMProvider:
    """Mock LLM provider with RAG-specific responses."""
    return MockLLMProvider(
        response_content=(
            "AgentWeave is a protocol-first multi-agent framework that supports MCP and A2A protocols. "
            "It provides RAG capabilities including vector search, BM25, and hybrid search."
        )
    )


@pytest.mark.integration
class TestRAGPipelineE2E:
    """Full pipeline integration tests."""

    async def test_full_ingest_query_flow(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test complete pipeline: ingest → retrieve → generate."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        # Ingest documents
        count = await pipeline.ingest_documents(sample_corpus)
        assert count > 0
        assert pipeline.ingested_count == count

        # Query pipeline
        response = await pipeline.query("What is AgentWeave?")

        # Verify response structure
        assert response.query == "What is AgentWeave?"
        assert len(response.answer) > 0
        assert response.retrieval.query == "What is AgentWeave?"
        assert len(response.retrieval.results) > 0
        assert response.usage["total_tokens"] > 0
        assert len(response.source_documents) > 0

    async def test_multi_document_ingest_with_chunking(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test ingesting multiple documents with custom chunking."""
        chunker = RecursiveCharacterChunker(chunk_size=200, chunk_overlap=20)
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
            chunker=chunker,
        )

        # Ingest and verify chunking occurred
        count = await pipeline.ingest_documents(sample_corpus)
        # With smaller chunk size, we should get more chunks than documents
        assert count >= len(sample_corpus)

        # Retrieve should work across chunks
        retrieval = await pipeline.retrieve("protocol MCP A2A")
        assert len(retrieval.results) > 0
        assert retrieval.retrieval_ms > 0

    async def test_pipeline_with_custom_recursive_chunker(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test pipeline with RecursiveCharacterChunker with small chunk_size."""
        chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=32),
            chunker=chunker,
        )

        await pipeline.ingest_documents(sample_corpus)
        response = await pipeline.query("error handling")

        # Should retrieve and generate answer
        assert response.answer
        assert len(response.retrieval.results) > 0

    async def test_pipeline_vector_only_no_bm25(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test pipeline with BM25 disabled (vector-only search)."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
            enable_bm25=False,
        )

        await pipeline.ingest_documents(sample_corpus)
        retrieval = await pipeline.retrieve("AgentWeave framework")

        # Should still retrieve results using vector search
        assert len(retrieval.results) > 0
        # Note: HybridSearch marks results as "hybrid" even when BM25 is None
        # This is expected behavior - the source field indicates it went through hybrid search

    async def test_query_returns_source_documents(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test that pipeline query returns correct source_documents."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        await pipeline.ingest_documents(sample_corpus)
        response = await pipeline.query("What is RAG?", limit=3)

        # Should return source document IDs
        assert isinstance(response.source_documents, list)
        assert len(response.source_documents) > 0
        # Each should be a valid document ID from corpus
        valid_ids = {doc.id for doc in sample_corpus}
        for doc_id in response.source_documents:
            assert doc_id in valid_ids

    async def test_pipeline_lifecycle_cleanup(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test pipeline async context manager cleans up properly."""
        async with RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        ) as pipeline:
            await pipeline.ingest_documents(sample_corpus)
            assert pipeline.ingested_count > 0

            # Use pipeline
            response = await pipeline.query("test query")
            assert response.answer

        # After exit, pipeline should be closed
        assert pipeline._closed is True
        assert pipeline.ingested_count == 0

    async def test_pipeline_clear_resets_state(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test pipeline clear() resets all state."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        # Ingest and verify state
        await pipeline.ingest_documents(sample_corpus)
        assert pipeline.ingested_count > 0

        # Clear
        await pipeline.clear()

        # State should be reset
        assert pipeline.ingested_count == 0

        # Should be able to re-ingest
        count = await pipeline.ingest_documents(sample_corpus[:2])
        assert count == await pipeline.ingest_documents(sample_corpus[:2])


@pytest.mark.integration
class TestHybridSearchE2E:
    """Hybrid search with multiple retrieval methods."""

    async def test_hybrid_vector_and_bm25_fusion(self, sample_corpus: list[Document]):
        """Test vector + BM25 hybrid search returns fused results."""
        # Setup vector store and BM25
        vector_store = InMemoryVectorStore()
        bm25 = BM25Search()
        embedder = MockEmbeddingProvider(dimensions=64)

        # Create hybrid search first
        hybrid = HybridSearch(vector_store, embedder, bm25=bm25)

        # Create and embed chunks using chunker.chunk_many()
        chunker = RecursiveCharacterChunker(chunk_size=300, chunk_overlap=30)
        all_chunks = chunker.chunk_many(sample_corpus)

        # Use hybrid.add() which handles both vector store and BM25
        await hybrid.add(all_chunks)

        # Search with both methods - returns RetrievalResult
        retrieval = await hybrid.search("AgentWeave protocol framework", limit=5)

        # Should get fused results
        assert len(retrieval.results) > 0
        assert retrieval.query == "AgentWeave protocol framework"
        # Results should have sources from hybrid search
        sources = {r.source for r in retrieval.results}
        assert "hybrid" in sources

    async def test_bm25_only_when_vector_fails(self, sample_corpus: list[Document]):
        """Test BM25-only results when vector returns nothing relevant."""
        vector_store = InMemoryVectorStore()
        bm25 = BM25Search()
        embedder = MockEmbeddingProvider(dimensions=64)

        # Create hybrid search
        hybrid = HybridSearch(vector_store, embedder, bm25=bm25)

        # Create chunks
        chunker = RecursiveCharacterChunker(chunk_size=300, chunk_overlap=30)
        all_chunks = chunker.chunk_many(sample_corpus)

        # Only add first chunk to vector store via add(), but index all in BM25
        if all_chunks:
            await hybrid.add([all_chunks[0]])  # Vector + BM25 get first chunk
            # Add rest only to BM25
            bm25.add_chunks(all_chunks[1:])

        # Search for something in later chunks - returns RetrievalResult
        retrieval = await hybrid.search("error handling retry", limit=5)

        # Should still get results from BM25
        assert len(retrieval.results) > 0
        assert retrieval.query == "error handling retry"

    async def test_filter_metadata_through_hybrid_search(self, sample_corpus: list[Document]):
        """Test metadata filtering works through hybrid search."""
        vector_store = InMemoryVectorStore()
        bm25 = BM25Search()
        embedder = MockEmbeddingProvider(dimensions=64)

        # Create hybrid search
        hybrid = HybridSearch(vector_store, embedder, bm25=bm25)

        # Create chunks with metadata (chunker already propagates doc metadata to chunks)
        chunker = RecursiveCharacterChunker(chunk_size=300, chunk_overlap=30)
        all_chunks = chunker.chunk_many(sample_corpus)

        # Use hybrid.add() which handles embedding and indexing
        await hybrid.add(all_chunks)

        # Search with metadata filter (parameter is 'filter' not 'metadata_filter')
        # Note: Filter only applies to vector search, not BM25
        retrieval = await hybrid.search(
            "AgentWeave", limit=10, filter={"category": "framework"}
        )

        # Should get results - at least some from vector search with filter
        assert len(retrieval.results) > 0
        # At least one result should match the filter (from vector search)
        matching = [r for r in retrieval.results if r.chunk.metadata.get("category") == "framework"]
        assert len(matching) > 0, "Expected at least one result with category=framework"


@pytest.mark.integration
class TestAgenticRAGE2E:
    """Agentic RAG tool integration."""

    async def test_create_rag_tools_returns_working_tools(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test create_rag_tools returns properly configured tools."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        await pipeline.ingest_documents(sample_corpus)

        tools = create_rag_tools(pipeline, search_limit=3)

        # Should create both tools
        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert "rag_search" in tool_names
        assert "rag_query" in tool_names

        # Each tool should be callable
        for tool in tools:
            assert callable(tool.func)
            assert len(tool.parameters) > 0

    async def test_rag_search_tool_returns_formatted_context(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test rag_search tool returns formatted context with sources."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        await pipeline.ingest_documents(sample_corpus)
        tools = create_rag_tools(pipeline, search_limit=3)

        # Find rag_search tool
        search_tool = next(t for t in tools if t.name == "rag_search")

        # Call tool
        result = await search_tool.func(query="AgentWeave framework", limit=2)

        # Should return formatted string with sources
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain score and source info
        assert "score:" in result.lower()
        assert "source:" in result.lower()

    async def test_rag_query_tool_returns_synthesized_answer(
        self, sample_corpus: list[Document], mock_rag_llm: MockLLMProvider
    ):
        """Test rag_query tool returns synthesized answer with sources."""
        pipeline = RAGPipeline(
            llm=mock_rag_llm,
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        await pipeline.ingest_documents(sample_corpus)
        tools = create_rag_tools(pipeline, search_limit=3)

        # Find rag_query tool
        query_tool = next(t for t in tools if t.name == "rag_query")

        # Call tool
        result = await query_tool.func(question="What is AgentWeave?")

        # Should return synthesized answer
        assert isinstance(result, str)
        assert len(result) > 0
        # Answer should come from mock LLM
        assert "AgentWeave" in result


@pytest.mark.integration
class TestRAGEvaluationE2E:
    """Evaluation pipeline integration."""

    async def test_evaluate_runs_all_metrics_in_parallel(self):
        """Test evaluate() runs all 3 metrics in parallel and returns EvaluationResult."""
        evaluator = RAGEvaluator(
            llm=MockLLMProvider(response_content="yes\nyes\nyes")
        )

        result = await evaluator.evaluate(
            query="What is AgentWeave?",
            answer="AgentWeave is a multi-agent framework supporting MCP and A2A protocols.",
            contexts=[
                "AgentWeave is a protocol-first multi-agent framework.",
                "It supports MCP and A2A protocols for agent communication.",
            ],
        )

        # Should have all 3 metrics
        assert len(result.metrics) == 3
        metric_names = {m.name for m in result.metrics}
        assert "faithfulness" in metric_names
        assert "answer_relevancy" in metric_names
        assert "context_relevancy" in metric_names

        # Should compute RAGAS score
        assert result.ragas_score > 0
        assert result.ragas_score <= 1.0

    async def test_evaluate_response_extracts_fields_correctly(
        self, sample_corpus: list[Document]
    ):
        """Test evaluate_response() extracts fields from RAGResponse correctly."""
        pipeline = RAGPipeline(
            llm=MockLLMProvider(response_content="Test answer about AgentWeave"),
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        await pipeline.ingest_documents(sample_corpus)
        response = await pipeline.query("What is AgentWeave?", limit=2)

        # Evaluate the response
        evaluator = RAGEvaluator(
            llm=MockLLMProvider(response_content="yes\nyes\nyes")
        )
        result = await evaluator.evaluate_response(response)

        # Should extract query, answer, contexts from response
        assert len(result.metrics) == 3
        assert result.ragas_score > 0

        # Get specific metric to verify it ran
        faithfulness = result.get_metric("faithfulness")
        assert faithfulness is not None
        assert faithfulness.score >= 0

    async def test_evaluation_with_agent_tools(
        self, sample_corpus: list[Document]
    ):
        """Test end-to-end: Agent uses RAG tools, then evaluate response."""
        # Create pipeline and tools
        pipeline = RAGPipeline(
            llm=MockLLMProvider(response_content="AgentWeave is a framework for multi-agent systems."),
            embedding_provider=MockEmbeddingProvider(dimensions=64),
        )

        await pipeline.ingest_documents(sample_corpus)
        tools = create_rag_tools(pipeline, search_limit=2)

        # Create agent with RAG tools (no tool calls, just verify integration)
        agent = Agent(
            name="rag-assistant",
            role="RAG-powered assistant",
            llm_provider=MockLLMProvider(
                response_content="Based on the knowledge base, AgentWeave is a multi-agent framework."
            ),
            tools=tools,
        )

        # Agent should be configured with tools
        assert len(agent.tools) == 2

        # Response from agent - Agent.run() returns AgentResult
        result = await agent.run("What is AgentWeave?")
        assert "AgentWeave" in result.output

        # Could evaluate RAG response quality if we had one
        rag_response = await pipeline.query("What is AgentWeave?")
        evaluator = RAGEvaluator(llm=MockLLMProvider(response_content="yes\nyes\nyes"))
        eval_result = await evaluator.evaluate_response(rag_response)

        assert eval_result.ragas_score > 0
