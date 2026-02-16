"""Test RAG node execution in the workflow executor.

This test suite verifies that the RAG node type is properly integrated
into the workflow executor and can execute retrieval-augmented generation tasks.
"""

import pytest

from app.core.executor import (
    WorkflowExecutor,
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    ExecutionStatus,
    ExecutionStateStore,
)
from app.core.mcp_manager import MCPManager
from app.core.secret_store import SecretStore


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager."""
    return MCPManager()


@pytest.fixture
def mock_secret_store():
    """Mock secret store."""
    class MockDB:
        async def execute(self, *args, **kwargs):
            pass
        async def fetchone(self, *args, **kwargs):
            return None
        async def fetchall(self, *args, **kwargs):
            return []
    return SecretStore(MockDB())


@pytest.fixture
def mock_state_store():
    """Mock state store."""
    class MockDB:
        async def execute(self, *args, **kwargs):
            pass
        async def fetchone(self, *args, **kwargs):
            return None
    return ExecutionStateStore(MockDB())


@pytest.fixture
def executor(mock_mcp_manager, mock_secret_store, mock_state_store):
    """Create executor instance."""
    return WorkflowExecutor(
        mcp_manager=mock_mcp_manager,
        secret_store=mock_secret_store,
        state_store=mock_state_store,
    )


@pytest.mark.asyncio
async def test_rag_node_mock_mode(executor):
    """Test RAG node execution in mock mode."""
    workflow = Workflow(
        id="wf-1",
        name="RAG Test",
        nodes=[
            WorkflowNode(
                id="node-1",
                type="rag",
                data={
                    "documents": [
                        "The capital of France is Paris.",
                        "The Eiffel Tower is located in Paris.",
                    ],
                    "searchLimit": 5,
                    "enableBm25": True,
                },
            ),
        ],
        edges=[],
    )

    result = await executor.run(workflow, "What is the capital of France?", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 1
    node_exec = result.node_executions[0]
    assert node_exec.status == ExecutionStatus.COMPLETED
    assert isinstance(node_exec.output, dict)
    assert "output" in node_exec.output
    assert "query" in node_exec.output
    assert "chunks" in node_exec.output
    assert "retrievalTimeMs" in node_exec.output


@pytest.mark.asyncio
async def test_rag_node_no_query(executor):
    """Test RAG node handles empty query gracefully."""
    workflow = Workflow(
        id="wf-1",
        name="RAG No Query",
        nodes=[
            WorkflowNode(
                id="node-1",
                type="rag",
                data={
                    "documents": ["Sample document."],
                },
            ),
        ],
        edges=[],
    )

    result = await executor.run(workflow, "", mode="full")

    assert result.status == ExecutionStatus.COMPLETED
    node_exec = result.node_executions[0]
    assert node_exec.status == ExecutionStatus.COMPLETED
    assert node_exec.output["output"] == "No query provided to RAG node."
    assert node_exec.output["query"] == ""
    assert node_exec.output["chunks"] == []


@pytest.mark.asyncio
async def test_rag_node_with_upstream_input(executor):
    """Test RAG node receives query from upstream node."""
    workflow = Workflow(
        id="wf-1",
        name="RAG with Upstream",
        nodes=[
            WorkflowNode(
                id="node-1",
                type="agent",
                data={
                    "name": "QueryGenerator",
                    "role": "Generate a query",
                },
            ),
            WorkflowNode(
                id="node-2",
                type="rag",
                data={
                    "documents": ["Paris is the capital of France."],
                    "inputSource": "node-1",
                },
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="node-1", target="node-2"),
        ],
    )

    # Run in mock mode to avoid LLM calls
    result = await executor.run(workflow, "Generate a query about France", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 2

    # Second node should be RAG node
    rag_exec = result.node_executions[1]
    assert rag_exec.node_id == "node-2"
    assert rag_exec.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_rag_node_custom_parameters(executor):
    """Test RAG node respects custom parameters in mock mode."""
    workflow = Workflow(
        id="wf-1",
        name="RAG Custom Params",
        nodes=[
            WorkflowNode(
                id="node-1",
                type="rag",
                data={
                    "documents": ["Sample text."],
                    "searchLimit": 10,
                    "chunkSize": 1000,
                    "chunkOverlap": 100,
                    "enableBm25": False,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "systemPrompt": "You are a helpful assistant.",
                },
            ),
        ],
        edges=[],
    )

    result = await executor.run(workflow, "Test query", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    node_exec = result.node_executions[0]
    assert node_exec.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_rag_node_empty_documents(executor):
    """Test RAG node handles empty documents list."""
    workflow = Workflow(
        id="wf-1",
        name="RAG Empty Docs",
        nodes=[
            WorkflowNode(
                id="node-1",
                type="rag",
                data={
                    "documents": [],
                },
            ),
        ],
        edges=[],
    )

    result = await executor.run(workflow, "Test query", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    node_exec = result.node_executions[0]
    assert node_exec.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_mock_output_rag(executor):
    """Test _get_mock_output returns proper structure for RAG node."""
    node = WorkflowNode(
        id="node-1",
        type="rag",
        data={"documents": ["Test"]},
    )

    output = executor._get_mock_output(node)

    assert isinstance(output, dict)
    assert "output" in output
    assert "query" in output
    assert "sources" in output
    assert "chunks" in output
    assert "retrievalTimeMs" in output
    assert isinstance(output["chunks"], list)
    if output["chunks"]:
        assert "content" in output["chunks"][0]
        assert "score" in output["chunks"][0]


@pytest.mark.asyncio
async def test_embedding_provider_openai_with_key(executor, monkeypatch):
    """Test OpenAI embedding provider is used when API key is configured."""
    from app.config import Settings
    from app.core.executor import WorkflowExecutor

    # Mock settings with OpenAI key
    settings = Settings(
        openai_api_key="sk-test-key",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
    )

    provider = WorkflowExecutor._create_embedding_provider(settings)

    assert provider.model_name == "text-embedding-3-small"
    assert provider.dimensions == 1536


@pytest.mark.asyncio
async def test_embedding_provider_openai_no_key_fallback(executor):
    """Test hash fallback when OpenAI provider selected but no API key."""
    from app.config import Settings
    from app.core.executor import WorkflowExecutor

    settings = Settings(
        openai_api_key="",
        embedding_provider="openai",
    )

    provider = WorkflowExecutor._create_embedding_provider(settings)

    assert provider.model_name == "hash-embedding"
    assert provider.dimensions == 32


@pytest.mark.asyncio
async def test_embedding_provider_ollama(executor):
    """Test Ollama embedding provider is used when configured."""
    from app.config import Settings
    from app.core.executor import WorkflowExecutor

    settings = Settings(
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        embedding_dimensions=768,
        ollama_base_url="http://localhost:11434",
    )

    provider = WorkflowExecutor._create_embedding_provider(settings)

    assert provider.model_name == "nomic-embed-text"
    assert provider.dimensions == 768


@pytest.mark.asyncio
async def test_embedding_provider_hash_explicit(executor):
    """Test hash provider when explicitly requested."""
    from app.config import Settings
    from app.core.executor import WorkflowExecutor

    settings = Settings(
        embedding_provider="hash",
    )

    provider = WorkflowExecutor._create_embedding_provider(settings)

    assert provider.model_name == "hash-embedding"
    assert provider.dimensions == 32


@pytest.mark.asyncio
async def test_hash_embedding_consistency(executor):
    """Test hash embedding produces consistent vectors for same text."""
    from app.core.executor import _HashEmbeddingProvider

    provider = _HashEmbeddingProvider()
    text = "test document"

    vec1 = await provider.embed(text)
    vec2 = await provider.embed(text)

    assert vec1 == vec2
    assert len(vec1) == 32
    assert all(0.0 <= v <= 1.0 for v in vec1)


@pytest.mark.asyncio
async def test_hash_embedding_batch(executor):
    """Test hash embedding batch processing."""
    from app.core.executor import _HashEmbeddingProvider

    provider = _HashEmbeddingProvider()
    texts = ["doc1", "doc2", "doc3"]

    vectors = await provider.embed_batch(texts)

    assert len(vectors) == 3
    assert all(len(v) == 32 for v in vectors)
    # Different texts should produce different vectors
    assert vectors[0] != vectors[1]
    assert vectors[1] != vectors[2]
