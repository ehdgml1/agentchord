"""Pytest configuration and fixtures for AgentWeave tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentweave.core.types import LLMResponse, Message, MessageRole, StreamChunk, ToolCall, Usage
from agentweave.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""

    def __init__(
        self,
        model: str = "mock-model",
        response_content: str = "Mock response",
        tool_calls: list[ToolCall] | None = None,
    ) -> None:
        self._model = model
        self._response_content = response_content
        self._tool_calls = tool_calls
        self.call_count = 0

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Mock complete implementation."""
        self.call_count += 1
        return LLMResponse(
            content=self._response_content,
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="tool_calls" if self._tool_calls else "stop",
            tool_calls=self._tool_calls,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Mock stream implementation."""
        self.call_count += 1
        content = self._response_content
        yield StreamChunk(
            content=content,
            delta=content,
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5),
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002


class MockToolCallProvider(BaseLLMProvider):
    """Mock provider that simulates tool calling behavior.

    First call returns tool_calls, subsequent calls return text.
    Useful for testing the tool execution loop.
    """

    def __init__(
        self,
        model: str = "mock-model",
        tool_calls_sequence: list[list[ToolCall] | None] | None = None,
        responses: list[str] | None = None,
    ) -> None:
        self._model = model
        self._tool_calls_sequence = tool_calls_sequence or [None]
        self._responses = responses or ["Final response"]
        self.call_count = 0
        self.received_messages: list[list[Message]] = []

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return tool_calls or text based on call sequence."""
        self.received_messages.append(list(messages))
        idx = self.call_count
        self.call_count += 1

        tool_calls = (
            self._tool_calls_sequence[idx]
            if idx < len(self._tool_calls_sequence)
            else None
        )
        response_text = (
            self._responses[idx]
            if idx < len(self._responses)
            else self._responses[-1]
        )

        return LLMResponse(
            content=response_text if not tool_calls else "",
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="tool_calls" if tool_calls else "stop",
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Mock stream."""
        self.call_count += 1
        yield StreamChunk(
            content="streamed",
            delta="streamed",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5),
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Create a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def mock_provider_factory():
    """Factory fixture for creating mock providers with custom responses."""

    def _factory(
        response_content: str = "Mock response",
        tool_calls: list[ToolCall] | None = None,
    ) -> MockLLMProvider:
        return MockLLMProvider(response_content=response_content, tool_calls=tool_calls)

    return _factory


@pytest.fixture
def mock_tool_call_provider_factory():
    """Factory for creating mock providers that simulate tool calling."""

    def _factory(
        tool_calls_sequence: list[list[ToolCall] | None] | None = None,
        responses: list[str] | None = None,
    ) -> MockToolCallProvider:
        return MockToolCallProvider(
            tool_calls_sequence=tool_calls_sequence,
            responses=responses,
        )

    return _factory


@pytest.fixture
def sample_messages() -> list[Message]:
    """Sample conversation messages for testing."""
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello!"),
        Message(role=MessageRole.ASSISTANT, content="Hi there! How can I help?"),
    ]


@pytest.fixture
def sample_usage() -> Usage:
    """Sample usage statistics."""
    return Usage(prompt_tokens=100, completion_tokens=50)


@pytest.fixture
def sample_llm_response(sample_usage: Usage) -> LLMResponse:
    """Sample LLM response."""
    return LLMResponse(
        content="This is a test response.",
        model="test-model",
        usage=sample_usage,
        finish_reason="stop",
    )


# ---------------------------------------------------------------------------
# RAG fixtures
# ---------------------------------------------------------------------------
from agentweave.rag.embeddings.base import EmbeddingProvider
from agentweave.rag.types import Chunk, Document


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, dimensions: int = 4) -> None:
        self._dimensions = dimensions
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "mock-embedding"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding from text hash."""
        self.call_count += 1
        return self._hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed using hash-based embeddings."""
        self.call_count += 1
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        """Create a deterministic embedding from text content."""
        h = hash(text)
        values = []
        for i in range(self._dimensions):
            values.append(((h >> (i * 8)) & 0xFF) / 255.0)
        # Normalize to unit vector
        magnitude = sum(v * v for v in values) ** 0.5
        if magnitude > 0:
            values = [v / magnitude for v in values]
        return values


@pytest.fixture
def mock_embedding_provider() -> MockEmbeddingProvider:
    """Create a mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.fixture
def sample_documents() -> list[Document]:
    """Sample documents for RAG testing."""
    return [
        Document(
            id="doc1",
            content="AgentWeave is a protocol-first multi-agent framework. "
                    "It supports MCP and A2A protocols for agent communication.",
            source="docs/readme.md",
            metadata={"type": "readme"},
        ),
        Document(
            id="doc2",
            content="The RAG module provides retrieval-augmented generation. "
                    "It includes vector search, BM25, and hybrid search.",
            source="docs/rag.md",
            metadata={"type": "docs"},
        ),
        Document(
            id="doc3",
            content="Python is a programming language. "
                    "It is widely used for machine learning and AI.",
            source="docs/python.md",
            metadata={"type": "docs"},
        ),
    ]


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    """Sample chunks with embeddings for testing."""
    return [
        Chunk(
            id="chunk1",
            content="AgentWeave is a multi-agent framework",
            document_id="doc1",
            embedding=[0.1, 0.2, 0.3, 0.4],
            metadata={"source": "readme"},
        ),
        Chunk(
            id="chunk2",
            content="RAG provides retrieval-augmented generation",
            document_id="doc2",
            embedding=[0.2, 0.3, 0.4, 0.5],
            metadata={"source": "rag"},
        ),
        Chunk(
            id="chunk3",
            content="Python is used for machine learning",
            document_id="doc3",
            embedding=[0.3, 0.4, 0.5, 0.6],
            metadata={"source": "python"},
        ),
    ]
