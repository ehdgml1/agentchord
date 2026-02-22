"""Tests for RAG pipeline."""
import pytest
from agentchord.rag.pipeline import RAGPipeline
from agentchord.rag.types import Document, RetrievalResult
from tests.conftest import MockLLMProvider, MockEmbeddingProvider


class TestRAGPipeline:
    @pytest.fixture
    def pipeline(self):
        return RAGPipeline(
            llm=MockLLMProvider(response_content="Generated answer"),
            embedding_provider=MockEmbeddingProvider(),
        )

    async def test_ingest_documents(self, pipeline, sample_documents):
        count = await pipeline.ingest_documents(sample_documents)
        assert count > 0
        assert pipeline.ingested_count == count

    async def test_ingest_empty(self, pipeline):
        count = await pipeline.ingest_documents([])
        assert count == 0

    async def test_retrieve_after_ingest(self, pipeline, sample_documents):
        await pipeline.ingest_documents(sample_documents)
        result = await pipeline.retrieve("AgentChord")
        assert isinstance(result, RetrievalResult)
        assert result.query == "AgentChord"

    async def test_generate(self, pipeline):
        retrieval = RetrievalResult(query="test")
        response = await pipeline.generate("test question", retrieval)
        assert response.answer == "Generated answer"
        assert response.query == "test question"

    async def test_query_end_to_end(self, pipeline, sample_documents):
        await pipeline.ingest_documents(sample_documents)
        response = await pipeline.query("What is AgentChord?")
        assert response.answer == "Generated answer"
        assert response.query == "What is AgentChord?"

    async def test_clear(self, pipeline, sample_documents):
        await pipeline.ingest_documents(sample_documents)
        assert pipeline.ingested_count > 0
        await pipeline.clear()
        assert pipeline.ingested_count == 0

    async def test_pipeline_without_bm25(self):
        pipeline = RAGPipeline(
            llm=MockLLMProvider(),
            embedding_provider=MockEmbeddingProvider(),
            enable_bm25=False,
        )
        docs = [Document(content="Test content for pipeline without BM25")]
        count = await pipeline.ingest_documents(docs)
        assert count > 0

    async def test_custom_system_prompt(self):
        pipeline = RAGPipeline(
            llm=MockLLMProvider(response_content="Custom answer"),
            embedding_provider=MockEmbeddingProvider(),
            system_prompt="Custom prompt: {context}",
        )
        docs = [Document(content="test document content")]
        await pipeline.ingest_documents(docs)
        response = await pipeline.query("question")
        assert response.answer == "Custom answer"

    async def test_generate_returns_usage(self, pipeline):
        retrieval = RetrievalResult(query="test")
        response = await pipeline.generate("q", retrieval)
        assert "prompt_tokens" in response.usage
        assert "completion_tokens" in response.usage
        assert "total_tokens" in response.usage

    async def test_generate_returns_source_documents(self, pipeline, sample_documents):
        await pipeline.ingest_documents(sample_documents)
        retrieval = await pipeline.retrieve("AgentChord")
        response = await pipeline.generate("What is AgentChord?", retrieval)
        # source_documents should contain unique document_ids from results
        assert isinstance(response.source_documents, list)

    async def test_retrieve_with_limit(self, pipeline, sample_documents):
        await pipeline.ingest_documents(sample_documents)
        result = await pipeline.retrieve("AgentChord", limit=1)
        assert len(result.results) <= 1

    async def test_ingested_count_accumulates(self, pipeline):
        docs1 = [Document(content="First batch of documents")]
        docs2 = [Document(content="Second batch of documents")]
        c1 = await pipeline.ingest_documents(docs1)
        c2 = await pipeline.ingest_documents(docs2)
        assert pipeline.ingested_count == c1 + c2

    async def test_generate_handles_llm_error(self):
        """Test M1: LLM API error handling in pipeline.generate()"""
        from unittest.mock import AsyncMock

        # Create a mock LLM that raises an error
        mock_llm = AsyncMock()
        mock_llm.complete.side_effect = Exception("LLM API failure")

        pipeline = RAGPipeline(
            llm=mock_llm,
            embedding_provider=MockEmbeddingProvider(),
        )

        retrieval = RetrievalResult(query="test")
        response = await pipeline.generate("test question", retrieval)

        # Should return error message instead of crashing
        assert "Failed to generate answer" in response.answer
        assert "LLM API failure" in response.answer
        assert response.usage == {}
        assert response.query == "test question"

    async def test_close_idempotent(self, pipeline, sample_documents):
        """Test close() can be called multiple times safely."""
        await pipeline.ingest_documents(sample_documents)
        assert pipeline.ingested_count > 0

        # First close
        await pipeline.close()
        assert pipeline.ingested_count == 0
        assert pipeline._closed is True

        # Second close should not raise
        await pipeline.close()
        assert pipeline._closed is True

    async def test_async_context_manager(self, sample_documents):
        """Test pipeline can be used as async context manager."""
        async with RAGPipeline(
            llm=MockLLMProvider(),
            embedding_provider=MockEmbeddingProvider(),
        ) as pipeline:
            await pipeline.ingest_documents(sample_documents)
            assert pipeline.ingested_count > 0
            response = await pipeline.query("test")
            assert response.answer == "Mock response"

        # Should be closed after exiting context
        assert pipeline._closed is True
        assert pipeline.ingested_count == 0

    async def test_context_manager_cleanup_on_exception(self, sample_documents):
        """Test pipeline cleanup happens even when exception occurs."""
        pipeline = None
        with pytest.raises(ValueError, match="Intentional error"):
            async with RAGPipeline(
                llm=MockLLMProvider(),
                embedding_provider=MockEmbeddingProvider(),
            ) as p:
                pipeline = p
                await p.ingest_documents(sample_documents)
                raise ValueError("Intentional error")

        # Should still be closed despite exception
        assert pipeline is not None
        assert pipeline._closed is True
        assert pipeline.ingested_count == 0
