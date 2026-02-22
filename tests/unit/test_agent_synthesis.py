"""Unit tests for Agent synthesis round after tool execution."""

from __future__ import annotations

import pytest

from agentchord import Agent
from agentchord.core.types import LLMResponse, Message, MessageRole, StreamChunk, ToolCall, Usage
from agentchord.tools.base import Tool, ToolParameter
from tests.conftest import MockLLMProvider


class SynthesisRoundProvider(MockLLMProvider):
    """Provider that returns empty content with tool_calls, then synthesis text."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0
        self.call_history: list[dict] = []

    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> LLMResponse:
        """First call: empty content + tool_calls. Second call: empty + no tools. Third: synthesis."""
        has_tools = "tools" in kwargs
        self.call_history.append({"has_tools": has_tools, "message_count": len(messages)})
        self.call_count += 1

        if self.call_count == 1:
            return LLMResponse(
                content="",
                model="mock-model",
                usage=Usage(prompt_tokens=10, completion_tokens=5),
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="mock_tool",
                        arguments={"arg": "value"},
                    )
                ],
            )
        elif self.call_count == 2:
            return LLMResponse(
                content="",
                model="mock-model",
                usage=Usage(prompt_tokens=12, completion_tokens=3),
                finish_reason="stop",
                tool_calls=None,
            )
        else:
            return LLMResponse(
                content="Synthesis response based on tool results",
                model="mock-model",
                usage=Usage(prompt_tokens=15, completion_tokens=10),
                finish_reason="stop",
                tool_calls=None,
            )

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ):
        """Stream synthesis response."""
        has_tools = "tools" in kwargs
        self.call_history.append({"has_tools": has_tools, "message_count": len(messages)})
        self.call_count += 1

        content = "Streamed synthesis"
        yield StreamChunk(
            content=content,
            delta=content,
            finish_reason="stop",
            usage=Usage(prompt_tokens=15, completion_tokens=10),
        )


class NonEmptyResponseProvider(MockLLMProvider):
    """Provider that returns non-empty content alongside tool_calls."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> LLMResponse:
        """Return tool_call with non-empty content."""
        self.call_count += 1

        if self.call_count == 1:
            return LLMResponse(
                content="I will use the tool",
                model="mock-model",
                usage=Usage(prompt_tokens=10, completion_tokens=5),
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="mock_tool",
                        arguments={"arg": "value"},
                    )
                ],
            )
        else:
            return LLMResponse(
                content="Final response after tool execution",
                model="mock-model",
                usage=Usage(prompt_tokens=12, completion_tokens=8),
                finish_reason="stop",
                tool_calls=None,
            )


class NoToolCallProvider(MockLLMProvider):
    """Provider that never calls tools."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> LLMResponse:
        """Return regular response without tool calls."""
        self.call_count += 1
        return LLMResponse(
            content="Direct response without tools",
            model="mock-model",
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
            tool_calls=None,
        )


def mock_tool_fn(arg: str) -> str:
    """Mock tool function."""
    return f"Tool result for {arg}"


@pytest.fixture
def mock_tool() -> Tool:
    """Create a mock tool for testing."""
    return Tool(
        name="mock_tool",
        description="A mock tool",
        func=mock_tool_fn,
        parameters=[
            ToolParameter(name="arg", type="string", description="Test argument")
        ],
    )


class TestAgentSynthesisRound:
    """Tests for synthesis round when tool execution produces empty final content."""

    @pytest.mark.asyncio
    async def test_synthesis_round_triggers_on_empty_content(self, mock_tool: Tool) -> None:
        """When tool execution produces empty content, synthesis round should trigger."""
        provider = SynthesisRoundProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        result = await agent.run("Test input")

        assert provider.call_count == 3
        assert result.output == "Synthesis response based on tool results"
        assert len(provider.call_history) == 3
        assert provider.call_history[0]["has_tools"] is True
        assert provider.call_history[1]["has_tools"] is True
        assert provider.call_history[2]["has_tools"] is False

    @pytest.mark.asyncio
    async def test_synthesis_round_accumulates_tokens(self, mock_tool: Tool) -> None:
        """Synthesis round tokens should be accumulated in final usage."""
        provider = SynthesisRoundProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        result = await agent.run("Test input")

        assert result.usage.prompt_tokens == 37
        assert result.usage.completion_tokens == 18
        assert result.usage.total_tokens == 55

    @pytest.mark.asyncio
    async def test_no_synthesis_when_content_not_empty(self, mock_tool: Tool) -> None:
        """When final content is non-empty, no synthesis round should happen."""
        provider = NonEmptyResponseProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        result = await agent.run("Test input")

        assert provider.call_count == 2
        assert result.output == "Final response after tool execution"

    @pytest.mark.asyncio
    async def test_no_synthesis_when_no_tools_used(self) -> None:
        """When no tools are used, no synthesis round should happen."""
        provider = NoToolCallProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
        )

        result = await agent.run("Test input")

        assert provider.call_count == 1
        assert result.output == "Direct response without tools"

    @pytest.mark.asyncio
    async def test_synthesis_round_includes_tool_results(self, mock_tool: Tool) -> None:
        """Synthesis round should include tool results in message history."""
        provider = SynthesisRoundProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        result = await agent.run("Test input")

        assert any(msg.role == MessageRole.TOOL for msg in result.messages)
        tool_messages = [msg for msg in result.messages if msg.role == MessageRole.TOOL]
        assert len(tool_messages) == 1
        assert "Tool result for value" in tool_messages[0].content

    @pytest.mark.asyncio
    async def test_synthesis_stream_triggers_on_empty_content(self, mock_tool: Tool) -> None:
        """Stream should trigger synthesis round when content is empty."""
        provider = SynthesisRoundProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        chunks = []
        async for chunk in agent.stream("Test input"):
            chunks.append(chunk)

        assert provider.call_count == 3
        assert len(chunks) > 0
        final_content = "".join(c.delta for c in chunks if c.delta)
        assert "Streamed synthesis" in final_content
        assert len(provider.call_history) == 3
        assert provider.call_history[0]["has_tools"] is True
        assert provider.call_history[1]["has_tools"] is True
        assert provider.call_history[2]["has_tools"] is False

    @pytest.mark.asyncio
    async def test_no_synthesis_stream_when_content_exists(self, mock_tool: Tool) -> None:
        """Stream should not trigger synthesis when content exists."""
        provider = NonEmptyResponseProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        chunks = []
        async for chunk in agent.stream("Test input"):
            chunks.append(chunk)

        assert provider.call_count == 2
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_synthesis_metadata_includes_round_count(self, mock_tool: Tool) -> None:
        """Result metadata should reflect the synthesis round."""
        provider = SynthesisRoundProvider()
        agent = Agent(
            name="test-agent",
            role="Test",
            llm_provider=provider,
            tools=[mock_tool],
        )

        result = await agent.run("Test input")

        assert result.metadata["tool_rounds"] == 2
        assert result.metadata["agent_name"] == "test-agent"
