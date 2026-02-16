"""Integration tests for Agent end-to-end flows.

Tests that exercise Agent with multiple subsystems wired together:
memory, cost tracking, callbacks, tools, and streaming.
"""

from __future__ import annotations

import pytest

from agentweave.core.agent import Agent
from agentweave.core.types import StreamChunk, ToolCall
from agentweave.memory.conversation import ConversationMemory
from agentweave.tools.decorator import tool
from agentweave.tracking.callbacks import CallbackContext, CallbackEvent, CallbackManager
from agentweave.tracking.cost import CostTracker
from tests.conftest import MockLLMProvider, MockToolCallProvider


@pytest.mark.integration
class TestAgentFullLifecycle:
    """Agent with all subsystems: memory + cost tracker + callbacks."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_single_run(self, wired_agent):
        """Single run with all subsystems active."""
        agent, memory, tracker, callbacks = wired_agent(response_content="Integration OK")

        events = []

        def on_event(ctx: CallbackContext):
            events.append(ctx.event)

        callbacks.register_global(on_event)

        result = await agent.run("Hello integration")

        # Verify output
        assert result.output == "Integration OK"
        assert result.metadata["agent_name"] == "integration-test"

        # Verify memory stored user + assistant
        assert len(memory) == 2
        entries = memory.get_recent(2)
        assert entries[0].content == "Hello integration"
        assert entries[1].content == "Integration OK"

        # Verify cost tracked
        summary = tracker.get_summary()
        assert summary.request_count == 1
        assert summary.total_tokens > 0

        # Verify callbacks fired
        assert CallbackEvent.AGENT_START in events
        assert CallbackEvent.LLM_START in events
        assert CallbackEvent.LLM_END in events
        assert CallbackEvent.AGENT_END in events

    @pytest.mark.asyncio
    async def test_multi_turn_memory_accumulation(self, wired_agent):
        """Multiple runs accumulate memory context."""
        agent, memory, tracker, _ = wired_agent(response_content="Response")

        await agent.run("First question")
        await agent.run("Second question")
        await agent.run("Third question")

        # Memory should have 6 entries (3 user + 3 assistant)
        assert len(memory) == 6

        # Cost tracker should have 3 requests
        summary = tracker.get_summary()
        assert summary.request_count == 3

    def test_run_sync_integration(self):
        """run_sync works with all subsystems."""
        memory = ConversationMemory()
        tracker = CostTracker()
        agent = Agent(
            name="sync-test",
            role="Sync tester",
            llm_provider=MockLLMProvider(response_content="Sync OK"),
            memory=memory,
            cost_tracker=tracker,
        )

        result = agent.run_sync("Sync input")

        assert result.output == "Sync OK"
        assert len(memory) == 2
        assert tracker.get_summary().request_count == 1


@pytest.mark.integration
class TestAgentToolCalling:
    """Agent with tools through full tool-calling loop."""

    @pytest.mark.asyncio
    async def test_tool_call_and_response(self):
        """Agent calls tool, gets result, produces final answer."""

        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id="call_1", name="add", arguments={"a": 3, "b": 4})],
                None,  # Second call returns text
            ],
            responses=["", "The sum is 7"],
        )

        tracker = CostTracker()
        events = []
        callbacks = CallbackManager()
        callbacks.register_global(lambda ctx: events.append(ctx.event))

        agent = Agent(
            name="calculator",
            role="Math helper",
            llm_provider=provider,
            tools=[add],
            cost_tracker=tracker,
            callbacks=callbacks,
        )

        result = await agent.run("What is 3 + 4?")

        assert result.output == "The sum is 7"
        assert result.metadata["tool_rounds"] == 2

        # Usage accumulated across 2 rounds
        assert result.usage.prompt_tokens == 20  # 10 * 2
        assert result.usage.completion_tokens == 10  # 5 * 2

        # Verify tool events fired
        assert CallbackEvent.TOOL_START in events
        assert CallbackEvent.TOOL_END in events

    @pytest.mark.asyncio
    async def test_multi_tool_single_round(self):
        """Agent calls multiple tools in one round."""

        @tool(description="Multiply numbers")
        def multiply(a: int, b: int) -> int:
            return a * b

        @tool(description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [
                    ToolCall(id="call_1", name="add", arguments={"a": 1, "b": 2}),
                    ToolCall(id="call_2", name="multiply", arguments={"a": 3, "b": 4}),
                ],
                None,
            ],
            responses=["", "Results: 3 and 12"],
        )

        agent = Agent(
            name="multi-tool",
            role="Calculator",
            llm_provider=provider,
            tools=[add, multiply],
        )

        result = await agent.run("Compute")
        assert result.output == "Results: 3 and 12"

    @pytest.mark.asyncio
    async def test_tool_error_in_result(self):
        """Tool execution error is passed back to LLM as error message."""

        @tool(description="Always fails")
        def failing_tool(x: str) -> str:
            raise ValueError("Tool failed!")

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id="call_1", name="failing_tool", arguments={"x": "test"})],
                None,
            ],
            responses=["", "I encountered an error"],
        )

        agent = Agent(
            name="error-handler",
            role="Error handler",
            llm_provider=provider,
            tools=[failing_tool],
        )

        result = await agent.run("Try the tool")
        assert result.output == "I encountered an error"

    @pytest.mark.asyncio
    async def test_max_tool_rounds_terminates_loop(self):
        """Agent stops after max_tool_rounds even if LLM keeps requesting tools."""
        @tool(description="Noop tool")
        def noop() -> str:
            return "done"

        # Provider always returns tool calls (infinite loop scenario)
        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id=f"call_{i}", name="noop", arguments={})]
                for i in range(20)
            ],
            responses=[""] * 20,
        )

        agent = Agent(
            name="loop-tester",
            role="Loop tester",
            llm_provider=provider,
            tools=[noop],
        )

        result = await agent.run("Loop forever", max_tool_rounds=3)

        # Should have stopped after 3 rounds
        assert provider.call_count == 3
        assert result.metadata["tool_rounds"] == 3


@pytest.mark.integration
class TestAgentStreaming:
    """Agent streaming with tools and cost tracking."""

    @pytest.mark.asyncio
    async def test_stream_with_cost_tracking(self):
        """Streaming tracks costs properly."""
        tracker = CostTracker()
        agent = Agent(
            name="streamer",
            role="Streamer",
            llm_provider=MockLLMProvider(response_content="Streamed output"),
            cost_tracker=tracker,
        )

        chunks = []
        async for chunk in agent.stream("Stream me"):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert tracker.get_summary().request_count == 1

    @pytest.mark.asyncio
    async def test_stream_with_tools_uses_complete(self):
        """When tools are available, stream uses complete() for tool rounds."""

        @tool(description="Get time")
        def get_time() -> str:
            return "12:00 PM"

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id="call_1", name="get_time", arguments={})],
                None,
            ],
            responses=["", "The time is 12:00 PM"],
        )

        agent = Agent(
            name="stream-tools",
            role="Streamer with tools",
            llm_provider=provider,
            tools=[get_time],
        )

        chunks = []
        async for chunk in agent.stream("What time is it?"):
            chunks.append(chunk)

        # Should get the final response as a chunk
        assert len(chunks) >= 1
        assert "12:00 PM" in chunks[-1].content


@pytest.mark.integration
class TestAgentMCPIntegration:
    """Agent with MCP client integration."""

    @pytest.mark.asyncio
    async def test_setup_mcp_registers_tools(self):
        """setup_mcp converts MCP tools and registers them."""
        from unittest.mock import AsyncMock, MagicMock

        from agentweave.protocols.mcp.types import MCPTool, MCPToolResult

        # Mock MCP client
        mock_mcp = MagicMock()
        mock_mcp.list_tools = AsyncMock(
            return_value=[
                MCPTool(
                    name="search",
                    description="Search the web",
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    server_id="mock-server",
                ),
            ]
        )
        mock_mcp.call_tool = AsyncMock(
            return_value=MCPToolResult(content="Search results here", is_error=False)
        )

        agent = Agent(
            name="mcp-agent",
            role="MCP test",
            llm_provider=MockLLMProvider(),
            mcp_client=mock_mcp,
        )

        tool_names = await agent.setup_mcp()

        assert tool_names == ["search"]
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "search"

    @pytest.mark.asyncio
    async def test_agent_runs_with_mcp_tools(self):
        """Agent can execute MCP tools in a tool-calling loop."""
        from unittest.mock import AsyncMock, MagicMock

        from agentweave.protocols.mcp.types import MCPTool, MCPToolResult

        mock_mcp = MagicMock()
        mock_mcp.list_tools = AsyncMock(
            return_value=[
                MCPTool(
                    name="lookup",
                    description="Look up info",
                    input_schema={
                        "type": "object",
                        "properties": {"term": {"type": "string"}},
                        "required": ["term"],
                    },
                    server_id="mock-server",
                ),
            ]
        )
        mock_mcp.call_tool = AsyncMock(
            return_value=MCPToolResult(content="Found: Python is great", is_error=False)
        )

        provider = MockToolCallProvider(
            tool_calls_sequence=[
                [ToolCall(id="call_1", name="lookup", arguments={"term": "Python"})],
                None,
            ],
            responses=["", "Python is great according to my lookup"],
        )

        agent = Agent(
            name="mcp-runner",
            role="MCP runner",
            llm_provider=provider,
            mcp_client=mock_mcp,
        )

        await agent.setup_mcp()
        result = await agent.run("Tell me about Python")

        assert result.output == "Python is great according to my lookup"
        mock_mcp.call_tool.assert_called_once_with("lookup", {"term": "Python"})
