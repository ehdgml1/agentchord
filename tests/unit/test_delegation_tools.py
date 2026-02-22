"""Unit tests for delegation and shared context tools."""

from __future__ import annotations

import pytest

from agentchord.core.agent import Agent
from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.shared_context import SharedContext
from agentchord.orchestration.tools import create_context_tools, create_delegation_tools
from agentchord.orchestration.types import MessageType, TeamMember, TeamRole
from tests.conftest import MockLLMProvider


class TestCreateDelegationTools:
    """Tests for create_delegation_tools factory."""

    def test_create_delegation_tools_creates_correct_count(self):
        """Should create one tool per team member."""
        provider1 = MockLLMProvider(response_content="Response 1")
        provider2 = MockLLMProvider(response_content="Response 2")
        agent1 = Agent(name="agent1", role="Role 1", llm_provider=provider1)
        agent2 = Agent(name="agent2", role="Role 2", llm_provider=provider2)

        members = [
            ("agent1", agent1, None),
            ("agent2", agent2, None),
        ]

        tools = create_delegation_tools(members)

        assert len(tools) == 2

    def test_delegation_tool_names(self):
        """Tool names should follow 'delegate_to_{name}' pattern."""
        provider = MockLLMProvider()
        agent = Agent(name="researcher", role="Research Specialist", llm_provider=provider)
        members = [("researcher", agent, None)]

        tools = create_delegation_tools(members)

        assert tools[0].name == "delegate_to_researcher"

    def test_delegation_tool_descriptions_include_role(self):
        """Tool descriptions should include the agent role."""
        provider = MockLLMProvider()
        agent = Agent(name="researcher", role="Research Specialist", llm_provider=provider)
        member_info = TeamMember(name="researcher", role=TeamRole.SPECIALIST)
        members = [("researcher", agent, member_info)]

        tools = create_delegation_tools(members)

        assert "specialist" in tools[0].description

    def test_delegation_tool_descriptions_include_capabilities(self):
        """Tool descriptions should include capabilities when provided."""
        provider = MockLLMProvider()
        agent = Agent(name="searcher", role="Web Searcher", llm_provider=provider)
        member_info = TeamMember(
            name="searcher",
            role=TeamRole.WORKER,
            capabilities=["web_search", "summarization"]
        )
        members = [("searcher", agent, member_info)]

        tools = create_delegation_tools(members)

        description = tools[0].description
        assert "web_search" in description
        assert "summarization" in description

    @pytest.mark.asyncio
    async def test_delegation_tool_execution(self):
        """Tool execution should call agent.run() with correct input."""
        provider = MockLLMProvider(response_content="Agent output")
        agent = Agent(name="worker", role="Worker", llm_provider=provider)
        members = [("worker", agent, None)]

        tools = create_delegation_tools(members)
        tool = tools[0]

        result = await tool.func(task_description="Do this task")

        assert result == "Agent output"
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_delegation_tool_with_context_param(self):
        """Tool should append context parameter to input."""
        provider = MockLLMProvider(response_content="Agent output")
        agent = Agent(name="worker", role="Worker", llm_provider=provider)
        members = [("worker", agent, None)]

        tools = create_delegation_tools(members)
        tool = tools[0]

        result = await tool.func(
            task_description="Do this task",
            context="Some additional context"
        )

        assert result == "Agent output"
        # The agent should have received the combined input
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_delegation_tool_with_message_bus(self):
        """Tool should send messages when message bus is provided."""
        provider = MockLLMProvider(response_content="Agent output")
        agent = Agent(name="worker", role="Worker", llm_provider=provider)
        message_bus = MessageBus()
        message_bus.register("coordinator")
        message_bus.register("worker")

        members = [("worker", agent, None)]
        tools = create_delegation_tools(members, message_bus=message_bus)
        tool = tools[0]

        result = await tool.func(task_description="Do this task")

        assert result == "Agent output"

        # Check that messages were sent
        history = message_bus.get_history()
        assert len(history) == 2

        # First message: coordinator -> worker (TASK)
        assert history[0].sender == "coordinator"
        assert history[0].recipient == "worker"
        assert history[0].message_type == MessageType.TASK
        assert history[0].content == "Do this task"

        # Second message: worker -> coordinator (RESULT)
        assert history[1].sender == "worker"
        assert history[1].recipient == "coordinator"
        assert history[1].message_type == MessageType.RESULT
        assert history[1].content == "Agent output"


class TestCreateContextTools:
    """Tests for create_context_tools factory."""

    def test_create_context_tools_creates_three_tools(self):
        """Should create read, write, and list tools."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context)

        assert len(tools) == 3

        tool_names = {t.name for t in tools}
        assert tool_names == {"read_shared_context", "write_shared_context", "list_shared_context"}

    @pytest.mark.asyncio
    async def test_read_context_tool(self):
        """Read tool should retrieve values from shared context."""
        shared_context = SharedContext(initial={"topic": "AI agents"})
        tools = create_context_tools(shared_context)
        read_tool = next(t for t in tools if t.name == "read_shared_context")

        result = await read_tool.func(key="topic")

        assert result == "AI agents"

    @pytest.mark.asyncio
    async def test_read_context_tool_missing_key(self):
        """Read tool should return error message for missing keys."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context)
        read_tool = next(t for t in tools if t.name == "read_shared_context")

        result = await read_tool.func(key="nonexistent")

        assert "No value found" in result
        assert "nonexistent" in result

    @pytest.mark.asyncio
    async def test_write_context_tool(self):
        """Write tool should store values in shared context."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context)
        write_tool = next(t for t in tools if t.name == "write_shared_context")

        result = await write_tool.func(key="findings", value="Important results")

        assert "Successfully stored" in result
        assert "findings" in result

        # Verify value was actually stored
        stored_value = await shared_context.get("findings")
        assert stored_value == "Important results"

    @pytest.mark.asyncio
    async def test_list_context_keys_tool(self):
        """List tool should return all keys in shared context."""
        shared_context = SharedContext(initial={"key1": "value1", "key2": "value2"})
        tools = create_context_tools(shared_context)
        list_tool = next(t for t in tools if t.name == "list_shared_context")

        result = await list_tool.func()

        assert "Available keys:" in result
        assert "key1" in result
        assert "key2" in result

    @pytest.mark.asyncio
    async def test_list_context_empty(self):
        """List tool should handle empty shared context."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context)
        list_tool = next(t for t in tools if t.name == "list_shared_context")

        result = await list_tool.func()

        assert "Shared context is empty" in result


class TestToolIntegration:
    """Integration tests combining delegation and context tools."""

    @pytest.mark.asyncio
    async def test_multiple_delegation_tools(self):
        """Should create and execute multiple delegation tools."""
        provider1 = MockLLMProvider(response_content="Researcher output")
        provider2 = MockLLMProvider(response_content="Writer output")

        agent1 = Agent(name="researcher", role="Research", llm_provider=provider1)
        agent2 = Agent(name="writer", role="Writer", llm_provider=provider2)

        members = [
            ("researcher", agent1, TeamMember(name="researcher", role=TeamRole.SPECIALIST)),
            ("writer", agent2, TeamMember(name="writer", role=TeamRole.WORKER)),
        ]

        tools = create_delegation_tools(members)

        assert len(tools) == 2

        # Execute researcher tool
        result1 = await tools[0].func(task_description="Research topic")
        assert result1 == "Researcher output"

        # Execute writer tool
        result2 = await tools[1].func(task_description="Write article")
        assert result2 == "Writer output"

    @pytest.mark.asyncio
    async def test_context_tool_workflow(self):
        """Should write, read, and list context in sequence."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context)

        write_tool = next(t for t in tools if t.name == "write_shared_context")
        read_tool = next(t for t in tools if t.name == "read_shared_context")
        list_tool = next(t for t in tools if t.name == "list_shared_context")

        # Write value
        write_result = await write_tool.func(key="data", value="test_value")
        assert "Successfully stored" in write_result

        # Read value
        read_result = await read_tool.func(key="data")
        assert read_result == "test_value"

        # List keys
        list_result = await list_tool.func()
        assert "data" in list_result


class TestCreateContextToolsAgentName:
    """Tests for create_context_tools agent_name parameter (M11)."""

    @pytest.mark.asyncio
    async def test_create_context_tools_with_custom_agent_name(self):
        """Write tool should use the provided agent_name."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context, agent_name="my-agent")
        write_tool = next(t for t in tools if t.name == "write_shared_context")

        await write_tool.func(key="result", value="data")

        # Verify the agent name was recorded in history
        history = await shared_context.get_history()
        assert len(history) == 1
        assert history[0].agent == "my-agent"

    @pytest.mark.asyncio
    async def test_create_context_tools_default_agent_name(self):
        """Write tool should use 'unknown' when no agent_name specified."""
        shared_context = SharedContext()
        tools = create_context_tools(shared_context)
        write_tool = next(t for t in tools if t.name == "write_shared_context")

        await write_tool.func(key="result", value="data")

        history = await shared_context.get_history()
        assert len(history) == 1
        assert history[0].agent == "unknown"


class TestCreateDelegationToolsSenderName:
    """Tests for create_delegation_tools sender_name parameter (M11)."""

    @pytest.mark.asyncio
    async def test_delegation_tool_with_custom_sender_name(self):
        """Delegation tools should use the provided sender_name in messages."""
        provider = MockLLMProvider(response_content="Output")
        agent = Agent(name="worker", role="Worker", llm_provider=provider)
        message_bus = MessageBus()
        message_bus.register("lead")
        message_bus.register("worker")

        members = [("worker", agent, None)]
        tools = create_delegation_tools(
            members, message_bus=message_bus, sender_name="lead"
        )

        await tools[0].func(task_description="Do work")

        history = message_bus.get_history()
        assert history[0].sender == "lead"
        assert history[1].recipient == "lead"

    @pytest.mark.asyncio
    async def test_delegation_tool_on_result_callback(self):
        """on_result callback should be invoked after delegation."""
        provider = MockLLMProvider(response_content="Result")
        agent = Agent(name="worker", role="Worker", llm_provider=provider)
        members = [("worker", agent, None)]

        results_received: list[tuple[str, str, str]] = []

        async def _on_result(name: str, role: str, result: object) -> None:
            results_received.append((name, role, result.output))  # type: ignore[attr-defined]

        tools = create_delegation_tools(members, on_result=_on_result)
        await tools[0].func(task_description="Task")

        assert len(results_received) == 1
        assert results_received[0] == ("worker", "worker", "Result")


class TestCoordinatorUsesPublicToolAPI:
    """Tests verifying coordinator strategy uses Agent public API (P0-1)."""

    @pytest.mark.asyncio
    async def test_coordinator_uses_public_context_managers(self):
        """Coordinator should use Agent.temporary_tools/with_extended_prompt, not private fields."""
        import inspect
        from agentchord.orchestration.strategies.coordinator import CoordinatorStrategy

        source = inspect.getsource(CoordinatorStrategy.execute)

        # Should NOT contain direct private field access
        assert "_tool_executor" not in source, (
            "CoordinatorStrategy should not access _tool_executor directly"
        )
        assert "_system_prompt" not in source, (
            "CoordinatorStrategy should not access _system_prompt directly"
        )

        # Should use public context manager API
        assert ".temporary_tools(" in source, (
            "CoordinatorStrategy should use temporary_tools() context manager"
        )
        assert ".with_extended_prompt(" in source, (
            "CoordinatorStrategy should use with_extended_prompt() context manager"
        )
