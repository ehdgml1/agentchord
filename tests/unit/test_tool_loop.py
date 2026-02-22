"""Tests for Agent tool execution loop."""

from __future__ import annotations

import pytest

from agentchord import Agent, AgentResult
from agentchord.core.types import Message, MessageRole, ToolCall, Usage
from agentchord.tools.base import Tool, ToolParameter, ToolResult
from agentchord.tools.decorator import tool
from tests.conftest import MockLLMProvider, MockToolCallProvider


def _make_add_tool():
    """Create a simple add tool for testing."""
    @tool(description="Add two numbers")
    def add(a: int, b: int) -> int:
        return a + b
    return add


def _make_echo_tool():
    """Create an echo tool for testing."""
    @tool(description="Echo input text")
    def echo(text: str) -> str:
        return f"Echo: {text}"
    return echo


def _make_failing_tool():
    """Create a tool that always fails."""
    @tool(description="Always fails")
    def fail_tool(msg: str) -> str:
        raise ValueError(f"Tool error: {msg}")
    return fail_tool


class TestToolLoopBasic:
    """Basic tool execution loop tests."""

    @pytest.mark.asyncio
    async def test_no_tools_no_loop(self) -> None:
        """Agent without tools should work as before (backward compatibility)."""
        provider = MockLLMProvider(response_content="Hello!")
        agent = Agent(name="test", role="Test", llm_provider=provider)

        result = await agent.run("Hi")

        assert result.output == "Hello!"
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_tools_but_no_tool_calls_in_response(self) -> None:
        """Agent with tools but LLM returns text (no tool calls)."""
        provider = MockLLMProvider(response_content="I can help without tools")
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("What is 2+2?")

        assert result.output == "I can help without tools"
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_single_tool_call(self) -> None:
        """Agent calls one tool, gets result, returns final text."""
        tool_calls = [ToolCall(id="tc_1", name="add", arguments={"a": 3, "b": 5})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "The answer is 8"],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("What is 3+5?")

        assert result.output == "The answer is 8"
        assert provider.call_count == 2  # 1st: tool call, 2nd: final text

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_one_response(self) -> None:
        """LLM returns multiple tool calls in a single response."""
        tool_calls = [
            ToolCall(id="tc_1", name="add", arguments={"a": 1, "b": 2}),
            ToolCall(id="tc_2", name="echo", arguments={"text": "hello"}),
        ]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "Done: 3 and Echo: hello"],
        )
        add_tool = _make_add_tool()
        echo_tool = _make_echo_tool()
        agent = Agent(
            name="test", role="Test", llm_provider=provider,
            tools=[add_tool, echo_tool],
        )

        result = await agent.run("Do both")

        assert result.output == "Done: 3 and Echo: hello"
        assert provider.call_count == 2

    @pytest.mark.asyncio
    async def test_multi_round_tool_calls(self) -> None:
        """Tool loop with multiple rounds: tool call -> result -> tool call -> result -> text."""
        round1_calls = [ToolCall(id="tc_1", name="add", arguments={"a": 1, "b": 2})]
        round2_calls = [ToolCall(id="tc_2", name="add", arguments={"a": 3, "b": 4})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[round1_calls, round2_calls, None],
            responses=["", "", "Results: 3 and 7"],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("Add 1+2 then 3+4")

        assert result.output == "Results: 3 and 7"
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_tool_execution_error_handled(self) -> None:
        """Tool that raises error should include error in message, not crash agent."""
        tool_calls = [ToolCall(id="tc_1", name="fail_tool", arguments={"msg": "oops"})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "Tool failed but I can still respond"],
        )
        fail_tool = _make_failing_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[fail_tool])

        result = await agent.run("Try the failing tool")

        assert result.output == "Tool failed but I can still respond"
        assert provider.call_count == 2
        # Check that error message was sent back to LLM
        second_call_msgs = provider.received_messages[1]
        tool_msg = [m for m in second_call_msgs if m.role == MessageRole.TOOL]
        assert len(tool_msg) == 1
        assert "Error:" in tool_msg[0].content


class TestToolLoopUsageTracking:
    """Tests for token/cost accumulation across tool rounds."""

    @pytest.mark.asyncio
    async def test_usage_accumulated_across_rounds(self) -> None:
        """Total tokens should sum across all LLM calls in tool loop."""
        tool_calls = [ToolCall(id="tc_1", name="add", arguments={"a": 1, "b": 2})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "Done"],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("Add 1+2")

        # MockToolCallProvider returns 10 prompt + 5 completion per call
        # 2 calls = 20 prompt + 10 completion
        assert result.usage.prompt_tokens == 20
        assert result.usage.completion_tokens == 10
        assert result.usage.total_tokens == 30

    @pytest.mark.asyncio
    async def test_cost_accumulated_across_rounds(self) -> None:
        """Cost should reflect total tokens across all rounds."""
        tool_calls = [ToolCall(id="tc_1", name="add", arguments={"a": 1, "b": 2})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "Done"],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("Add 1+2")

        # MockProvider: $0.001/1K input, $0.002/1K output
        # 20 input = $0.00002, 10 output = $0.00002
        expected_cost = (20 / 1000 * 0.001) + (10 / 1000 * 0.002)
        assert result.cost == pytest.approx(expected_cost, rel=1e-6)


class TestToolLoopMaxRounds:
    """Tests for max_tool_rounds limit."""

    @pytest.mark.asyncio
    async def test_max_tool_rounds_default(self) -> None:
        """Default max_tool_rounds should be 10."""
        # Create a provider that always returns tool calls (infinite loop scenario)
        always_tool_calls = [ToolCall(id="tc", name="add", arguments={"a": 1, "b": 1})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[always_tool_calls] * 15,  # More than default 10
            responses=[""] * 15,
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("Loop forever")

        # Should stop at 10 rounds (default)
        assert provider.call_count == 10

    @pytest.mark.asyncio
    async def test_custom_max_tool_rounds(self) -> None:
        """Custom max_tool_rounds should be respected."""
        always_tool_calls = [ToolCall(id="tc", name="add", arguments={"a": 1, "b": 1})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[always_tool_calls] * 10,
            responses=[""] * 10,
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("Loop", max_tool_rounds=3)

        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_max_tool_rounds_one_means_no_loop(self) -> None:
        """max_tool_rounds=1 should allow at most 1 LLM call (no loop)."""
        tool_calls = [ToolCall(id="tc", name="add", arguments={"a": 1, "b": 1})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls],
            responses=[""],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("Once", max_tool_rounds=1)

        assert provider.call_count == 1


class TestToolLoopMessages:
    """Tests for message history during tool loop."""

    @pytest.mark.asyncio
    async def test_tool_messages_in_conversation(self) -> None:
        """Tool call and result messages should be in conversation history."""
        tool_calls = [ToolCall(id="tc_1", name="add", arguments={"a": 2, "b": 3})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "The sum is 5"],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = await agent.run("What is 2+3?")

        # Second LLM call should have: system, user, assistant(tool_calls), tool(result)
        second_msgs = provider.received_messages[1]
        roles = [m.role for m in second_msgs]
        assert MessageRole.SYSTEM in roles
        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles
        assert MessageRole.TOOL in roles

        # Tool message should contain the result
        tool_msgs = [m for m in second_msgs if m.role == MessageRole.TOOL]
        assert len(tool_msgs) == 1
        assert "5" in tool_msgs[0].content
        assert tool_msgs[0].tool_call_id == "tc_1"

    @pytest.mark.asyncio
    async def test_assistant_message_has_tool_calls(self) -> None:
        """Assistant message should carry tool_calls when present."""
        tool_calls = [ToolCall(id="tc_1", name="echo", arguments={"text": "hi"})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "Done"],
        )
        echo_tool = _make_echo_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[echo_tool])

        result = await agent.run("Echo something")

        second_msgs = provider.received_messages[1]
        assistant_msgs = [m for m in second_msgs if m.role == MessageRole.ASSISTANT]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0].tool_calls is not None
        assert len(assistant_msgs[0].tool_calls) == 1
        assert assistant_msgs[0].tool_calls[0].name == "echo"


class TestToolLoopBackwardCompat:
    """Tests ensuring backward compatibility."""

    @pytest.mark.asyncio
    async def test_existing_tests_still_pass(self) -> None:
        """Agent without tools should behave identically to before."""
        provider = MockLLMProvider(response_content="Hello!")
        agent = Agent(name="test", role="Test", llm_provider=provider)

        result = await agent.run("Hi")

        assert isinstance(result, AgentResult)
        assert result.output == "Hello!"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.metadata["agent_name"] == "test"
        assert result.metadata["provider"] == "mock"

    def test_run_sync_with_tools(self) -> None:
        """run_sync should work with tool loop."""
        tool_calls = [ToolCall(id="tc_1", name="add", arguments={"a": 1, "b": 1})]
        provider = MockToolCallProvider(
            tool_calls_sequence=[tool_calls, None],
            responses=["", "2"],
        )
        add_tool = _make_add_tool()
        agent = Agent(name="test", role="Test", llm_provider=provider, tools=[add_tool])

        result = agent.run_sync("1+1")

        assert result.output == "2"
        assert provider.call_count == 2
