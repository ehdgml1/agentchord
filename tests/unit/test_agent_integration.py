"""Unit tests for Agent integration features."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentchord.core.agent import Agent
from agentchord.core.types import LLMResponse, Usage, StreamChunk
from agentchord.memory.conversation import ConversationMemory
from agentchord.memory.base import MemoryEntry
from agentchord.tracking.cost import CostTracker
from agentchord.tracking.callbacks import CallbackManager, CallbackEvent, CallbackContext
from agentchord.tools.decorator import tool
from agentchord.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response_content: str = "Mock response") -> None:
        self._response_content = response_content
        self._model = "mock-model"

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

    async def complete(self, messages, **kwargs) -> LLMResponse:
        return LLMResponse(
            content=self._response_content,
            model=self._model,
            usage=Usage(prompt_tokens=100, completion_tokens=50),
            finish_reason="stop",
        )

    async def stream(self, messages, **kwargs):
        words = self._response_content.split()
        content = ""
        for i, word in enumerate(words):
            content += word + " " if i < len(words) - 1 else word
            yield StreamChunk(
                content=content,
                delta=word + (" " if i < len(words) - 1 else ""),
            )
        yield StreamChunk(
            content=content,
            delta="",
            finish_reason="stop",
            usage=Usage(prompt_tokens=100, completion_tokens=50),
        )


class TestAgentWithMemory:
    """Tests for Agent with Memory integration."""

    @pytest.mark.asyncio
    async def test_memory_stores_conversation(self) -> None:
        """Agent should store conversation in memory."""
        memory = ConversationMemory()
        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(),
            memory=memory,
        )

        await agent.run("Hello!")

        assert len(memory) == 2  # User + Assistant
        entries = memory.get_recent(2)
        assert entries[0].role == "user"
        assert entries[0].content == "Hello!"
        assert entries[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_memory_provides_context(self) -> None:
        """Agent should use memory for context."""
        memory = ConversationMemory()
        memory.add(MemoryEntry(content="Previous question", role="user"))
        memory.add(MemoryEntry(content="Previous answer", role="assistant"))

        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(),
            memory=memory,
        )

        result = await agent.run("New question")

        # Should have loaded 2 from memory + system + new user
        assert len(result.messages) >= 4


class TestAgentWithCostTracker:
    """Tests for Agent with CostTracker integration."""

    @pytest.mark.asyncio
    async def test_tracks_cost(self) -> None:
        """Agent should track costs."""
        tracker = CostTracker()
        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(),
            cost_tracker=tracker,
        )

        await agent.run("Hello!")

        summary = tracker.get_summary()
        assert summary.request_count == 1
        assert summary.total_tokens > 0

    @pytest.mark.asyncio
    async def test_tracks_agent_name(self) -> None:
        """Cost entries should include agent name."""
        tracker = CostTracker()
        agent = Agent(
            name="researcher",
            role="Test agent",
            llm_provider=MockLLMProvider(),
            cost_tracker=tracker,
        )

        await agent.run("Hello!")

        entries = tracker.get_entries()
        assert entries[0].agent_name == "researcher"


class TestAgentWithCallbacks:
    """Tests for Agent with Callbacks integration."""

    @pytest.mark.asyncio
    async def test_emits_lifecycle_events(self) -> None:
        """Agent should emit lifecycle events."""
        manager = CallbackManager()
        events: list[CallbackEvent] = []

        def on_event(ctx: CallbackContext) -> None:
            events.append(ctx.event)

        manager.register_global(on_event)

        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(),
            callbacks=manager,
        )

        await agent.run("Hello!")

        # Should have: agent_start, llm_start, llm_end, agent_end
        assert CallbackEvent.AGENT_START in events
        assert CallbackEvent.LLM_START in events
        assert CallbackEvent.LLM_END in events
        assert CallbackEvent.AGENT_END in events


class TestAgentWithTools:
    """Tests for Agent with Tools integration."""

    def test_tools_property(self) -> None:
        """Should expose registered tools."""
        @tool(description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(),
            tools=[add],
        )

        assert len(agent.tools) == 1
        assert agent.tools[0].name == "add"


class TestAgentStreaming:
    """Tests for Agent streaming."""

    @pytest.mark.asyncio
    async def test_stream_basic(self) -> None:
        """Agent should stream responses."""
        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(response_content="Hello world"),
        )

        chunks = []
        async for chunk in agent.stream("Hi"):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[-1].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_stream_with_cost_tracker(self) -> None:
        """Stream should track costs on final chunk."""
        tracker = CostTracker()
        agent = Agent(
            name="test",
            role="Test agent",
            llm_provider=MockLLMProvider(response_content="Hello world"),
            cost_tracker=tracker,
        )

        async for _ in agent.stream("Hi"):
            pass

        summary = tracker.get_summary()
        assert summary.request_count == 1


class TestAgentProperties:
    """Tests for Agent property accessors."""

    def test_memory_property(self) -> None:
        """Should expose memory."""
        memory = ConversationMemory()
        agent = Agent(
            name="test",
            role="Test",
            llm_provider=MockLLMProvider(),
            memory=memory,
        )

        assert agent.memory is memory

    def test_cost_tracker_property(self) -> None:
        """Should expose cost tracker."""
        tracker = CostTracker()
        agent = Agent(
            name="test",
            role="Test",
            llm_provider=MockLLMProvider(),
            cost_tracker=tracker,
        )

        assert agent.cost_tracker is tracker

    def test_none_when_not_configured(self) -> None:
        """Should return None when not configured."""
        agent = Agent(
            name="test",
            role="Test",
            llm_provider=MockLLMProvider(),
        )

        assert agent.memory is None
        assert agent.cost_tracker is None
        assert agent.tools == []
