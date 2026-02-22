"""Tests for Agent.temporary_tools() and Agent.with_extended_prompt() context managers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agentchord.core.agent import Agent
from agentchord.tools.base import Tool, ToolParameter


def _make_mock_provider():
    """Create a mock LLM provider for testing."""
    provider = MagicMock()
    provider.provider_name = "openai"
    provider.calculate_cost.return_value = 0.001

    response = MagicMock()
    response.content = "test output"
    response.tool_calls = []
    response.finish_reason = "stop"
    response.usage = MagicMock()
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 20
    response.usage.total_tokens = 30

    provider.complete = AsyncMock(return_value=response)
    return provider


def _make_dummy_tool(name: str = "test_tool") -> Tool:
    """Create a dummy tool for testing."""
    async def _func(x: str = "") -> str:
        return f"result_{x}"

    return Tool(
        name=name,
        description=f"Test tool {name}",
        parameters=[
            ToolParameter(name="x", type="string", description="input", required=False)
        ],
        func=_func,
    )


class TestTemporaryTools:
    """Tests for Agent.temporary_tools() context manager."""

    @pytest.mark.asyncio
    async def test_adds_tools_inside_context(self):
        """Tools are available inside the context."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider)

        assert agent.tools == []

        tool = _make_dummy_tool("temp_tool")
        async with agent.temporary_tools([tool]):
            assert len(agent.tools) == 1
            assert agent.tools[0].name == "temp_tool"

    @pytest.mark.asyncio
    async def test_removes_tools_after_context(self):
        """Tools are removed after exiting the context."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider)

        tool = _make_dummy_tool("temp_tool")
        async with agent.temporary_tools([tool]):
            pass

        assert agent.tools == []
        assert agent._tool_executor is None

    @pytest.mark.asyncio
    async def test_preserves_existing_tools(self):
        """Existing tools are preserved after context exit."""
        provider = _make_mock_provider()
        existing_tool = _make_dummy_tool("existing")
        agent = Agent(name="test", role="tester", llm_provider=provider, tools=[existing_tool])

        assert len(agent.tools) == 1

        new_tool = _make_dummy_tool("temporary")
        async with agent.temporary_tools([new_tool]):
            assert len(agent.tools) == 2
            tool_names = {t.name for t in agent.tools}
            assert tool_names == {"existing", "temporary"}

        assert len(agent.tools) == 1
        assert agent.tools[0].name == "existing"

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self):
        """Tools are cleaned up even if an exception occurs."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider)

        tool = _make_dummy_tool("temp_tool")
        with pytest.raises(ValueError):
            async with agent.temporary_tools([tool]):
                raise ValueError("test error")

        assert agent.tools == []
        assert agent._tool_executor is None

    @pytest.mark.asyncio
    async def test_multiple_tools(self):
        """Multiple tools can be added at once."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider)

        tools = [_make_dummy_tool(f"tool_{i}") for i in range(3)]
        async with agent.temporary_tools(tools):
            assert len(agent.tools) == 3

        assert agent.tools == []

    @pytest.mark.asyncio
    async def test_yields_agent(self):
        """Context manager yields the agent itself."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider)

        tool = _make_dummy_tool()
        async with agent.temporary_tools([tool]) as ctx_agent:
            assert ctx_agent is agent


class TestWithExtendedPrompt:
    """Tests for Agent.with_extended_prompt() context manager."""

    @pytest.mark.asyncio
    async def test_extends_prompt_inside_context(self):
        """System prompt is extended inside the context."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider, system_prompt="Original prompt")

        async with agent.with_extended_prompt("Extension text"):
            assert "Original prompt" in agent.system_prompt
            assert "Extension text" in agent.system_prompt

    @pytest.mark.asyncio
    async def test_restores_prompt_after_context(self):
        """System prompt is restored after exiting the context."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider, system_prompt="Original prompt")

        async with agent.with_extended_prompt("Extension text"):
            pass

        assert agent.system_prompt == "Original prompt"
        assert "Extension" not in agent.system_prompt

    @pytest.mark.asyncio
    async def test_sets_prompt_when_none(self):
        """When no system prompt exists, extension becomes the prompt."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider)

        async with agent.with_extended_prompt("New prompt"):
            assert agent._system_prompt == "New prompt"

        assert agent._system_prompt is None

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self):
        """Prompt is restored even if an exception occurs."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider, system_prompt="Original")

        with pytest.raises(ValueError):
            async with agent.with_extended_prompt("Extension"):
                raise ValueError("test error")

        assert agent.system_prompt == "Original"

    @pytest.mark.asyncio
    async def test_yields_agent(self):
        """Context manager yields the agent itself."""
        provider = _make_mock_provider()
        agent = Agent(name="test", role="tester", llm_provider=provider, system_prompt="Original")

        async with agent.with_extended_prompt("Ext") as ctx_agent:
            assert ctx_agent is agent


class TestAgentTeamClosePropagate:
    """Tests for AgentTeam.close() propagating to child agents."""

    @pytest.mark.asyncio
    async def test_close_propagates_to_agents(self):
        """close() calls close() on all child agents."""
        agent1 = MagicMock()
        agent1.name = "agent1"
        agent1.run = AsyncMock()
        agent1.close = AsyncMock()

        agent2 = MagicMock()
        agent2.name = "agent2"
        agent2.run = AsyncMock()
        agent2.close = AsyncMock()

        from agentchord.orchestration.team import AgentTeam
        team = AgentTeam(name="test-team", members=[agent1, agent2])
        await team.close()

        agent1.close.assert_awaited_once()
        agent2.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_continues_on_error(self):
        """If one agent's close() fails, others still get closed."""
        agent1 = MagicMock()
        agent1.name = "agent1"
        agent1.run = AsyncMock()
        agent1.close = AsyncMock(side_effect=RuntimeError("close failed"))

        agent2 = MagicMock()
        agent2.name = "agent2"
        agent2.run = AsyncMock()
        agent2.close = AsyncMock()

        from agentchord.orchestration.team import AgentTeam
        team = AgentTeam(name="test-team", members=[agent1, agent2])
        await team.close()  # Should not raise

        agent1.close.assert_awaited_once()
        agent2.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Calling close() twice doesn't close agents twice."""
        agent1 = MagicMock()
        agent1.name = "agent1"
        agent1.run = AsyncMock()
        agent1.close = AsyncMock()

        from agentchord.orchestration.team import AgentTeam
        team = AgentTeam(name="test-team", members=[agent1])
        await team.close()
        await team.close()  # Second call should be no-op

        agent1.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_via_context_manager(self):
        """close() is called when using async with."""
        agent1 = MagicMock()
        agent1.name = "agent1"
        agent1.run = AsyncMock()
        agent1.close = AsyncMock()

        from agentchord.orchestration.team import AgentTeam
        async with AgentTeam(name="test-team", members=[agent1]) as team:
            pass

        agent1.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_handles_agents_without_close(self):
        """Agents without close() method are safely skipped."""
        agent1 = MagicMock(spec=["name", "run"])  # No close method
        agent1.name = "agent1"
        agent1.run = AsyncMock()

        from agentchord.orchestration.team import AgentTeam
        team = AgentTeam(name="test-team", members=[agent1])
        await team.close()  # Should not raise
