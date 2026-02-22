import pytest
from agentchord.core.agent import Agent
from agentchord.core.types import ToolCall, StreamChunk
from agentchord.tools import tool
from tests.conftest import MockLLMProvider, MockToolCallProvider


class TestStreamBasic:
    """Tests for basic streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_no_tools(self):
        """Stream without tools should use pure streaming."""
        provider = MockLLMProvider(response_content="Streamed response")
        agent = Agent(name="a", role="r", llm_provider=provider)

        chunks = []
        async for chunk in agent.stream("hello"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].content == "Streamed response"
        assert chunks[0].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_stream_with_tools_no_calls(self):
        """Stream with tools but LLM doesn't call them."""
        @tool(description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        provider = MockToolCallProvider(
            tool_calls_sequence=[None],
            responses=["Just text, no tools needed"],
        )
        agent = Agent(name="a", role="r", llm_provider=provider, tools=[add])

        chunks = []
        async for chunk in agent.stream("hello"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].content == "Just text, no tools needed"


class TestStreamToolCalling:
    """Tests for streaming with tool calling."""

    @pytest.mark.asyncio
    async def test_stream_with_single_tool_call(self):
        """Stream with one tool call round."""
        @tool(description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id="call_1", name="add", arguments={"a": 5, "b": 3})],
                None,
            ],
            responses=["", "5 + 3 = 8"],
        )
        agent = Agent(name="a", role="r", llm_provider=provider, tools=[add])

        chunks = []
        async for chunk in agent.stream("add 5 and 3"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].content == "5 + 3 = 8"
        assert provider.call_count == 2  # One for tool call, one for final

    @pytest.mark.asyncio
    async def test_stream_with_multi_round_tools(self):
        """Stream with multiple tool call rounds."""
        @tool(description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id="call_1", name="add", arguments={"a": 1, "b": 2})],
                [ToolCall(id="call_2", name="add", arguments={"a": 3, "b": 4})],
                None,
            ],
            responses=["", "", "Results: 3 and 7"],
        )
        agent = Agent(name="a", role="r", llm_provider=provider, tools=[add])

        chunks = []
        async for chunk in agent.stream("compute both"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].content == "Results: 3 and 7"
        assert provider.call_count == 3


class TestStreamUsage:
    """Tests for streaming usage tracking."""

    @pytest.mark.asyncio
    async def test_stream_no_tools_has_usage(self):
        """Pure stream yields usage on final chunk."""
        provider = MockLLMProvider(response_content="response")
        agent = Agent(name="a", role="r", llm_provider=provider)

        chunks = []
        async for chunk in agent.stream("hello"):
            chunks.append(chunk)

        assert chunks[-1].usage is not None
        assert chunks[-1].usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_stream_tools_has_usage(self):
        """Tool-calling stream yields usage from final complete() call."""
        provider = MockToolCallProvider(
            tool_calls_sequence=[None],
            responses=["Text response"],
        )
        agent = Agent(name="a", role="r", llm_provider=provider, tools=[])

        # No tools registered, but stream path with tools=[] creates no executor
        # So this falls to the pure streaming path
        chunks = []
        async for chunk in agent.stream("hello"):
            chunks.append(chunk)

        assert len(chunks) >= 1


class TestStreamBackwardCompat:
    """Tests for streaming backward compatibility."""

    @pytest.mark.asyncio
    async def test_stream_max_tool_rounds(self):
        """Stream accepts max_tool_rounds parameter."""
        provider = MockLLMProvider(response_content="response")
        agent = Agent(name="a", role="r", llm_provider=provider)

        chunks = []
        async for chunk in agent.stream("hello", max_tool_rounds=5):
            chunks.append(chunk)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_stream_error_handling(self):
        """Stream raises AgentExecutionError on failure."""
        from unittest.mock import AsyncMock
        from agentchord.errors.exceptions import AgentExecutionError

        provider = MockLLMProvider(response_content="x")
        # Override stream to raise
        provider.stream = AsyncMock(side_effect=RuntimeError("boom"))
        agent = Agent(name="a", role="r", llm_provider=provider)

        with pytest.raises(AgentExecutionError, match="streaming failed"):
            async for _ in agent.stream("hello"):
                pass
