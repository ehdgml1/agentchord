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

    # Mock settings with OpenAI key
    settings = Settings(
        openai_api_key="sk-test-key",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
    )

    provider = await executor._create_embedding_provider(settings)

    assert provider.model_name == "text-embedding-3-small"
    assert provider.dimensions == 1536


@pytest.mark.asyncio
async def test_embedding_provider_openai_no_key_fallback(executor):
    """Test hash fallback when OpenAI provider selected but no API key."""
    from app.config import Settings

    settings = Settings(
        openai_api_key="",
        embedding_provider="openai",
    )

    provider = await executor._create_embedding_provider(settings)

    assert provider.model_name == "hash-embedding"
    assert provider.dimensions == 32


@pytest.mark.asyncio
async def test_embedding_provider_ollama(executor):
    """Test Ollama embedding provider is used when configured."""
    from app.config import Settings

    settings = Settings(
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        embedding_dimensions=768,
        ollama_base_url="http://localhost:11434",
    )

    provider = await executor._create_embedding_provider(settings)

    assert provider.model_name == "nomic-embed-text"
    assert provider.dimensions == 768


@pytest.mark.asyncio
async def test_embedding_provider_hash_explicit(executor):
    """Test hash provider when explicitly requested."""
    from app.config import Settings

    settings = Settings(
        embedding_provider="hash",
    )

    provider = await executor._create_embedding_provider(settings)

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


# --- Tests for RAG structured upstream input extraction ---


@pytest.mark.asyncio
async def test_extract_rag_query_from_dict_with_query_field(executor):
    """Test _extract_rag_query extracts 'query' field from structured upstream dict."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "agent-classifier": {
            "category": "FAQ",
            "query": "프로 요금제 가격 정보",
            "urgency": "LOW",
        }
    }
    # Set up edges so rag-1 sees agent-classifier as upstream
    executor._current_edges = [
        WorkflowEdge(id="e1", source="agent-classifier", target="rag-1")
    ]

    result = executor._extract_rag_query(node, context)
    assert result == "프로 요금제 가격 정보"


@pytest.mark.asyncio
async def test_extract_rag_query_from_dict_with_output_field(executor):
    """Test _extract_rag_query uses 'output' field when no 'query' field."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "agent-1": {
            "output": "What is the capital of France?",
            "score": 95,
        }
    }
    executor._current_edges = [
        WorkflowEdge(id="e1", source="agent-1", target="rag-1")
    ]

    result = executor._extract_rag_query(node, context)
    assert result == "What is the capital of France?"


@pytest.mark.asyncio
async def test_extract_rag_query_from_dict_json_fallback(executor):
    """Test _extract_rag_query JSON-serializes dict when no query/output fields."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "agent-1": {
            "category": "billing",
            "urgency": "high",
        }
    }
    executor._current_edges = [
        WorkflowEdge(id="e1", source="agent-1", target="rag-1")
    ]

    result = executor._extract_rag_query(node, context)
    import json
    parsed = json.loads(result)
    assert parsed == {"category": "billing", "urgency": "high"}


@pytest.mark.asyncio
async def test_extract_rag_query_plain_string_passthrough(executor):
    """Test _extract_rag_query falls back to _resolve_input for string upstream output."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "input": "simple text query",
    }
    # No edges set
    executor._current_edges = []

    result = executor._extract_rag_query(node, context)
    assert result == "simple text query"


@pytest.mark.asyncio
async def test_extract_rag_query_prefers_query_over_output(executor):
    """Test _extract_rag_query prefers 'query' field over 'output' field."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "agent-1": {
            "query": "specific search query",
            "output": "general output text",
        }
    }
    executor._current_edges = [
        WorkflowEdge(id="e1", source="agent-1", target="rag-1")
    ]

    result = executor._extract_rag_query(node, context)
    assert result == "specific search query"


@pytest.mark.asyncio
async def test_rag_with_input_template(executor):
    """Test RAG node uses inputTemplate when set, resolved via template engine."""
    workflow = Workflow(
        id="wf-1",
        name="RAG Template",
        nodes=[
            WorkflowNode(
                id="agent-1",
                type="agent",
                data={
                    "name": "classifier",
                    "role": "Classify queries",
                    "outputFields": [
                        {"name": "query", "type": "text"},
                        {"name": "category", "type": "text"},
                    ],
                },
            ),
            WorkflowNode(
                id="rag-1",
                type="rag",
                data={
                    "documents": ["Sample knowledge base content."],
                    "inputTemplate": "{{agent-1.query}} 에 대해 검색하세요",
                },
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="agent-1", target="rag-1"),
        ],
    )

    result = await executor.run(workflow, "프로 요금제 알려줘", mode="mock")
    assert result.status == ExecutionStatus.COMPLETED

    rag_exec = result.node_executions[1]
    assert rag_exec.node_id == "rag-1"
    assert rag_exec.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_rag_structured_upstream_extracts_query_in_mock(executor):
    """Test RAG node in mock mode receives structured upstream output and extracts query."""
    # In mock mode, agent with outputFields returns a dict.
    # RAG should extract 'query' field from that dict.
    workflow = Workflow(
        id="wf-1",
        name="RAG Structured",
        nodes=[
            WorkflowNode(
                id="agent-1",
                type="agent",
                data={
                    "name": "classifier",
                    "role": "Classify",
                    "outputFields": [
                        {"name": "query", "type": "text"},
                        {"name": "category", "type": "text"},
                    ],
                },
            ),
            WorkflowNode(
                id="rag-1",
                type="rag",
                data={
                    "documents": ["Paris is the capital of France."],
                },
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="agent-1", target="rag-1"),
        ],
    )

    result = await executor.run(workflow, "Tell me about France", mode="mock")
    assert result.status == ExecutionStatus.COMPLETED

    rag_exec = result.node_executions[1]
    assert rag_exec.node_id == "rag-1"
    assert rag_exec.status == ExecutionStatus.COMPLETED
    # The RAG node should have received a meaningful query, not a stringified dict
    assert isinstance(rag_exec.output, dict)
    assert "query" in rag_exec.output


@pytest.mark.asyncio
async def test_extract_rag_query_skips_empty_query_field(executor):
    """Test _extract_rag_query skips empty query field and falls back to output."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "agent-1": {
            "query": "",
            "output": "fallback output text",
        }
    }
    executor._current_edges = [
        WorkflowEdge(id="e1", source="agent-1", target="rag-1")
    ]

    result = executor._extract_rag_query(node, context)
    assert result == "fallback output text"


@pytest.mark.asyncio
async def test_extract_rag_query_no_edges_uses_resolve_input(executor):
    """Test _extract_rag_query with no _current_edges attribute falls back to _resolve_input."""
    node = WorkflowNode(id="rag-1", type="rag", data={"documents": []})
    context = {
        "input": "direct workflow input",
    }
    # Ensure _current_edges not set
    if hasattr(executor, '_current_edges'):
        delattr(executor, '_current_edges')

    result = executor._extract_rag_query(node, context)
    assert result == "direct workflow input"


# --- Tests for _resolve_template with dict outputs ---


def test_resolve_template_with_dict_output_full_path(executor):
    """Test _resolve_template with {{nodeId.output}} when context[nodeId] is a dict."""
    template = "{{agent-1.output}}"
    context = {
        "agent-1": {
            "category": "FAQ",
            "query": "프로 요금제 가격",
            "urgency": "LOW"
        }
    }

    result = executor._resolve_template(template, context)

    # Should be JSON-serialized dict
    import json
    parsed = json.loads(result)
    assert parsed == {"category": "FAQ", "query": "프로 요금제 가격", "urgency": "LOW"}


def test_resolve_template_with_dict_specific_field(executor):
    """Test _resolve_template with {{nodeId.query}} for specific field access."""
    template = "Search for {{agent-1.query}}"
    context = {
        "agent-1": {
            "category": "FAQ",
            "query": "프로 요금제 가격",
            "urgency": "LOW"
        }
    }

    result = executor._resolve_template(template, context)
    assert result == "Search for 프로 요금제 가격"


def test_resolve_template_preserves_string_output_behavior(executor):
    """Test _resolve_template still handles string outputs correctly."""
    template = "{{agent-1.output}}"
    context = {
        "agent-1": "This is a plain string output"
    }

    result = executor._resolve_template(template, context)
    assert result == "This is a plain string output"


def test_resolve_template_mixed_dict_and_string_context(executor):
    """Test _resolve_template handles mixed context with dict and string values."""
    template = "{{agent-1.output}} and {{agent-2.score}}"
    context = {
        "agent-1": "simple text",
        "agent-2": {"score": 95, "category": "high"}
    }

    result = executor._resolve_template(template, context)
    assert result == "simple text and 95"


def test_resolve_template_nested_field_in_dict(executor):
    """Test _resolve_template can traverse nested fields in dict."""
    template = "Category: {{agent-1.category}}, Query: {{agent-1.query}}"
    context = {
        "agent-1": {
            "category": "billing",
            "query": "refund policy",
            "metadata": {"source": "web"}
        }
    }

    result = executor._resolve_template(template, context)
    assert result == "Category: billing, Query: refund policy"


@pytest.mark.asyncio
async def test_input_template_with_structured_upstream_dict(executor):
    """Test inputTemplate resolves both specific fields and .output from structured upstream dict."""
    workflow = Workflow(
        id="wf-1",
        name="Template Test",
        nodes=[
            WorkflowNode(
                id="agent-classifier",
                type="agent",
                data={
                    "name": "Classifier",
                    "role": "Classify user query",
                    "outputFields": [
                        {"name": "category", "type": "text"},
                        {"name": "query", "type": "text"},
                        {"name": "urgency", "type": "text"},
                    ],
                },
            ),
            WorkflowNode(
                id="rag-1",
                type="rag",
                data={
                    "documents": ["Sample knowledge base."],
                    "inputTemplate": "카테고리: {{agent-classifier.category}}, 쿼리: {{agent-classifier.query}}",
                },
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="agent-classifier", target="rag-1"),
        ],
    )

    result = await executor.run(workflow, "프로 요금제는?", mode="mock")
    assert result.status == ExecutionStatus.COMPLETED

    # First node returns structured dict in mock mode
    agent_exec = result.node_executions[0]
    assert isinstance(agent_exec.output, dict)
    assert "category" in agent_exec.output
    assert "query" in agent_exec.output

    # Second node should have template resolved with actual field values
    rag_exec = result.node_executions[1]
    assert rag_exec.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_input_template_with_output_on_dict_upstream(executor):
    """Test inputTemplate with {{nodeId.output}} serializes dict to JSON."""
    workflow = Workflow(
        id="wf-1",
        name="Template Output",
        nodes=[
            WorkflowNode(
                id="agent-1",
                type="agent",
                data={
                    "name": "Generator",
                    "role": "Generate data",
                    "outputFields": [
                        {"name": "title", "type": "text"},
                        {"name": "score", "type": "number"},
                    ],
                },
            ),
            WorkflowNode(
                id="agent-2",
                type="agent",
                data={
                    "name": "Processor",
                    "role": "Process data",
                    "inputTemplate": "Process this: {{agent-1.output}}",
                },
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="agent-1", target="agent-2"),
        ],
    )

    result = await executor.run(workflow, "Generate data", mode="mock")
    assert result.status == ExecutionStatus.COMPLETED

    # First node returns structured dict
    agent1_exec = result.node_executions[0]
    assert isinstance(agent1_exec.output, dict)

    # Second node should succeed (template resolved dict to JSON)
    agent2_exec = result.node_executions[1]
    assert agent2_exec.status == ExecutionStatus.COMPLETED
