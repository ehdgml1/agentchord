"""Tests for Agentic RAG tools."""
import pytest
from agentweave.rag.pipeline import RAGPipeline
from agentweave.rag.tools import create_rag_tools
from agentweave.rag.types import Document
from tests.conftest import MockLLMProvider, MockEmbeddingProvider


class TestCreateRAGTools:
    @pytest.fixture
    async def pipeline_with_data(self):
        pipeline = RAGPipeline(
            llm=MockLLMProvider(response_content="Tool answer"),
            embedding_provider=MockEmbeddingProvider(),
        )
        await pipeline.ingest_documents([
            Document(content="AgentWeave is a framework for building AI agents."),
        ])
        return pipeline

    async def test_returns_two_tools(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "rag_search" in names
        assert "rag_query" in names

    async def test_tool_schemas(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        for tool in tools:
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "function" in schema
            assert "parameters" in schema["function"]

    async def test_rag_search_execution(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        search_tool = next(t for t in tools if t.name == "rag_search")
        result = await search_tool.execute(query="AgentWeave")
        assert result.success
        assert isinstance(result.result, str)

    async def test_rag_query_execution(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        query_tool = next(t for t in tools if t.name == "rag_query")
        result = await query_tool.execute(question="What is AgentWeave?")
        assert result.success
        assert "Tool answer" in result.result

    async def test_search_no_results(self):
        pipeline = RAGPipeline(
            llm=MockLLMProvider(),
            embedding_provider=MockEmbeddingProvider(),
        )
        tools = create_rag_tools(pipeline)
        search_tool = next(t for t in tools if t.name == "rag_search")
        result = await search_tool.execute(query="nonexistent topic")
        assert result.success
        assert "No relevant" in result.result

    async def test_search_tool_has_query_param(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        search_tool = next(t for t in tools if t.name == "rag_search")
        param_names = [p.name for p in search_tool.parameters]
        assert "query" in param_names

    async def test_query_tool_has_question_param(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        query_tool = next(t for t in tools if t.name == "rag_query")
        param_names = [p.name for p in query_tool.parameters]
        assert "question" in param_names

    async def test_tools_are_async(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        for tool in tools:
            assert tool.is_async

    async def test_anthropic_schema(self, pipeline_with_data):
        tools = create_rag_tools(pipeline_with_data)
        for tool in tools:
            schema = tool.to_anthropic_schema()
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema
