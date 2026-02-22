"""Tests for Worker Consult feature (create_consult_tools and strategy integration)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentchord.core.agent import Agent
from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.strategies.base import StrategyContext
from agentchord.orchestration.strategies.debate import DebateStrategy
from agentchord.orchestration.strategies.map_reduce import MapReduceStrategy
from agentchord.orchestration.strategies.round_robin import RoundRobinStrategy
from agentchord.orchestration.team import AgentTeam
from agentchord.orchestration.tools import create_consult_tools
from agentchord.orchestration.types import TeamMember, TeamRole

from tests.conftest import MockLLMProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_agent(name: str, output: str = "mock response") -> AsyncMock:
    """Create a mock agent that mimics the Agent interface."""
    agent = AsyncMock()
    agent.name = name
    agent.run = AsyncMock(return_value=MagicMock(
        output=output,
        usage=MagicMock(total_tokens=100),
        cost=0.01,
        duration_ms=100,
    ))
    return agent


def _make_real_agent(name: str, response: str = "Mock response") -> Agent:
    """Create a real Agent with a MockLLMProvider."""
    return Agent(
        name=name,
        role=f"{name} role",
        model="mock-model",
        llm_provider=MockLLMProvider(response_content=response),
    )


# ===========================================================================
# create_consult_tools unit tests
# ===========================================================================


class TestCreateConsultTools:
    """Tests for create_consult_tools factory."""

    def test_creates_tools_for_each_peer(self) -> None:
        """One tool per peer, excluding self."""
        a1 = _make_mock_agent("agent1")
        a2 = _make_mock_agent("agent2")
        a3 = _make_mock_agent("agent3")
        peers = [
            ("agent1", a1, TeamMember(name="agent1")),
            ("agent2", a2, TeamMember(name="agent2")),
            ("agent3", a3, TeamMember(name="agent3")),
        ]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        assert len(tools) == 2  # excludes self
        names = {t.name for t in tools}
        assert names == {"consult_agent2", "consult_agent3"}

    def test_excludes_self(self) -> None:
        """No tool is created when only self is in the peer list."""
        a1 = _make_mock_agent("agent1")
        peers = [("agent1", a1, TeamMember(name="agent1"))]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        assert len(tools) == 0

    def test_empty_at_max_depth(self) -> None:
        """Returns empty list when _current_depth >= max_depth."""
        a1 = _make_mock_agent("agent1")
        peers = [("agent1", a1, TeamMember(name="agent1"))]
        tools = create_consult_tools(
            peers=peers, current_agent_name="x",
            max_depth=1, _current_depth=1,
        )
        assert len(tools) == 0

    def test_empty_at_depth_exceeding_max(self) -> None:
        """Returns empty when depth > max."""
        a2 = _make_mock_agent("agent2")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(
            peers=peers, current_agent_name="agent1",
            max_depth=2, _current_depth=3,
        )
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_consult_tool_calls_agent_run(self) -> None:
        """Consult tool invokes the peer agent's run method."""
        a2 = _make_mock_agent("agent2", output="the answer is 42")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        result = await tools[0].func(message="what is the answer?")
        assert result == "the answer is 42"
        a2.run.assert_awaited_once_with("what is the answer?")

    @pytest.mark.asyncio
    async def test_consult_sends_messages_to_bus(self) -> None:
        """Consult records TASK and RESPONSE messages on the message bus."""
        bus = MessageBus()
        bus.register("agent1")
        bus.register("agent2")
        a2 = _make_mock_agent("agent2")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(
            peers=peers, current_agent_name="agent1", message_bus=bus,
        )
        await tools[0].func(message="question")
        history = bus.get_history()
        assert len(history) == 2  # TASK + RESPONSE
        assert history[0].sender == "agent1"
        assert history[0].recipient == "agent2"
        assert history[0].metadata.get("type") == "consult"
        assert history[1].sender == "agent2"
        assert history[1].recipient == "agent1"
        assert history[1].metadata.get("type") == "consult"

    @pytest.mark.asyncio
    async def test_on_consult_callback(self) -> None:
        """on_consult callback is invoked with agent name and result."""
        callback = AsyncMock()
        a2 = _make_mock_agent("agent2")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(
            peers=peers, current_agent_name="agent1",
            on_consult=callback,
        )
        await tools[0].func(message="check this")
        callback.assert_awaited_once()
        args = callback.call_args[0]
        assert args[0] == "agent2"

    def test_tool_description_includes_capabilities(self) -> None:
        """Tool description mentions role and capabilities."""
        a2 = _make_mock_agent("agent2")
        member = TeamMember(
            name="agent2", role=TeamRole.SPECIALIST,
            capabilities=["data_analysis"],
        )
        peers = [("agent2", a2, member)]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        assert "data_analysis" in tools[0].description
        assert "specialist" in tools[0].description

    def test_tool_description_default_role(self) -> None:
        """Default role is worker when member_info has no explicit role override."""
        a2 = _make_mock_agent("agent2")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        assert "worker" in tools[0].description

    def test_tool_description_no_member_info(self) -> None:
        """Works when member_info is None."""
        a2 = _make_mock_agent("agent2")
        peers = [("agent2", a2, None)]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        assert len(tools) == 1
        assert "worker" in tools[0].description

    def test_tool_has_message_parameter(self) -> None:
        """Consult tool has a required 'message' parameter."""
        a2 = _make_mock_agent("agent2")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        assert len(tools[0].parameters) == 1
        assert tools[0].parameters[0].name == "message"
        assert tools[0].parameters[0].required is True

    @pytest.mark.asyncio
    async def test_multiple_consult_tools_independent(self) -> None:
        """Each consult tool calls the correct peer agent."""
        a2 = _make_mock_agent("agent2", output="from agent2")
        a3 = _make_mock_agent("agent3", output="from agent3")
        peers = [
            ("agent2", a2, TeamMember(name="agent2")),
            ("agent3", a3, TeamMember(name="agent3")),
        ]
        tools = create_consult_tools(peers=peers, current_agent_name="agent1")
        tool_map = {t.name: t for t in tools}

        result2 = await tool_map["consult_agent2"].func(message="q2")
        result3 = await tool_map["consult_agent3"].func(message="q3")

        assert result2 == "from agent2"
        assert result3 == "from agent3"
        a2.run.assert_awaited_once_with("q2")
        a3.run.assert_awaited_once_with("q3")

    @pytest.mark.asyncio
    async def test_no_message_bus_still_works(self) -> None:
        """Consult works without message bus."""
        a2 = _make_mock_agent("agent2", output="no bus")
        peers = [("agent2", a2, TeamMember(name="agent2"))]
        tools = create_consult_tools(
            peers=peers, current_agent_name="agent1",
            message_bus=None,
        )
        result = await tools[0].func(message="test")
        assert result == "no bus"


# ===========================================================================
# Strategy Integration Tests
# ===========================================================================


class TestConsultRoundRobinIntegration:
    """Test consult tool injection in RoundRobinStrategy."""

    @pytest.mark.asyncio
    async def test_round_robin_with_consult(self) -> None:
        """Round robin injects consult tools when enabled."""
        a1 = _make_real_agent("agent1", response="A1 output")
        a2 = _make_real_agent("agent2", response="A2 output")

        # Spy on temporary_tools to capture what tools are injected
        captured_tools: dict[str, list[str]] = {}
        for agent in [a1, a2]:
            original = agent.temporary_tools

            @asynccontextmanager
            async def spy(tools: Any, _orig: Any = original, _name: str = agent.name) -> Any:
                captured_tools[_name] = [t.name for t in tools]
                async with _orig(tools):
                    yield agent

            agent.temporary_tools = spy  # type: ignore[assignment]

        strategy = RoundRobinStrategy()
        ctx = StrategyContext(
            members=[TeamMember(name="agent1"), TeamMember(name="agent2")],
            enable_consult=True,
            max_consult_depth=1,
        )

        result = await strategy.execute(
            "task", {"agent1": a1, "agent2": a2}, ctx,
        )

        assert result.output  # should complete
        assert "agent1" in captured_tools
        assert "agent2" in captured_tools
        assert "consult_agent2" in captured_tools["agent1"]
        assert "consult_agent1" in captured_tools["agent2"]

    @pytest.mark.asyncio
    async def test_round_robin_without_consult(self) -> None:
        """Round robin does NOT inject tools when consult disabled."""
        a1 = _make_real_agent("agent1", response="A1 output")
        a2 = _make_real_agent("agent2", response="A2 output")

        captured_calls: list[str] = []
        for agent in [a1, a2]:
            original = agent.temporary_tools

            @asynccontextmanager
            async def spy(tools: Any, _orig: Any = original, _name: str = agent.name) -> Any:
                captured_calls.append(_name)
                async with _orig(tools):
                    yield agent

            agent.temporary_tools = spy  # type: ignore[assignment]

        strategy = RoundRobinStrategy()
        ctx = StrategyContext(enable_consult=False)

        result = await strategy.execute(
            "task", {"agent1": a1, "agent2": a2}, ctx,
        )

        assert result.output
        assert len(captured_calls) == 0  # temporary_tools should NOT be called


class TestConsultDebateIntegration:
    """Test consult tool injection in DebateStrategy."""

    @pytest.mark.asyncio
    async def test_debate_with_consult(self) -> None:
        """Debate injects consult tools during debate rounds."""
        a1 = _make_real_agent("agent1", response="A1 position")
        a2 = _make_real_agent("agent2", response="A2 position")

        captured_tools: dict[str, list[str]] = {}
        for agent in [a1, a2]:
            original = agent.temporary_tools

            @asynccontextmanager
            async def spy(tools: Any, _orig: Any = original, _name: str = agent.name) -> Any:
                captured_tools[_name] = [t.name for t in tools]
                async with _orig(tools):
                    yield agent

            agent.temporary_tools = spy  # type: ignore[assignment]

        strategy = DebateStrategy()
        ctx = StrategyContext(
            members=[TeamMember(name="agent1"), TeamMember(name="agent2")],
            enable_consult=True,
            max_rounds=1,
        )

        result = await strategy.execute(
            "topic", {"agent1": a1, "agent2": a2}, ctx,
        )

        assert result.output
        # Both should get consult tools during debate rounds
        assert "agent1" in captured_tools
        assert "agent2" in captured_tools
        assert "consult_agent2" in captured_tools["agent1"]
        assert "consult_agent1" in captured_tools["agent2"]

    @pytest.mark.asyncio
    async def test_debate_synthesis_no_consult(self) -> None:
        """Synthesis phase does NOT inject consult tools."""
        a1 = _make_real_agent("agent1", response="A1 position")

        consult_call_count = 0
        original = a1.temporary_tools

        @asynccontextmanager
        async def spy(tools: Any) -> Any:
            nonlocal consult_call_count
            consult_call_count += 1
            async with original(tools):
                yield a1

        a1.temporary_tools = spy  # type: ignore[assignment]

        strategy = DebateStrategy()
        ctx = StrategyContext(
            members=[TeamMember(name="agent1")],
            enable_consult=True,
            max_rounds=1,
        )

        await strategy.execute("topic", {"agent1": a1}, ctx)

        # Only 1 call for the debate round, NOT for synthesis
        # (single agent has no peers, so consult_tools is empty but
        # temporary_tools is still called for consistency)
        # Actually, with single agent, peers for "agent1" is empty
        # but the code still wraps it in temporary_tools
        assert consult_call_count == 1  # debate round only


class TestConsultMapReduceIntegration:
    """Test consult tool injection in MapReduceStrategy."""

    @pytest.mark.asyncio
    async def test_map_reduce_consult_only_reduce_phase(self) -> None:
        """Map-reduce only injects consult tools for reducer, not map workers."""
        a1 = _make_real_agent("agent1", response="A1 data")
        a2 = _make_real_agent("agent2", response="A2 data")

        consult_agents: list[str] = []
        for agent in [a1, a2]:
            original = agent.temporary_tools

            @asynccontextmanager
            async def spy(tools: Any, _orig: Any = original, _name: str = agent.name) -> Any:
                consult_agents.append(_name)
                async with _orig(tools):
                    yield agent

            agent.temporary_tools = spy  # type: ignore[assignment]

        strategy = MapReduceStrategy()
        ctx = StrategyContext(
            members=[TeamMember(name="agent1"), TeamMember(name="agent2")],
            enable_consult=True,
        )

        result = await strategy.execute(
            "task", {"agent1": a1, "agent2": a2}, ctx,
        )

        assert result.output
        # Only reducer (agent1) should get consult tools, not during map phase
        assert consult_agents == ["agent1"]

    @pytest.mark.asyncio
    async def test_map_reduce_without_consult(self) -> None:
        """Map-reduce does NOT inject tools when consult disabled."""
        a1 = _make_real_agent("agent1", response="A1 data")
        a2 = _make_real_agent("agent2", response="A2 data")

        consult_agents: list[str] = []
        for agent in [a1, a2]:
            original = agent.temporary_tools

            @asynccontextmanager
            async def spy(tools: Any, _orig: Any = original, _name: str = agent.name) -> Any:
                consult_agents.append(_name)
                async with _orig(tools):
                    yield agent

            agent.temporary_tools = spy  # type: ignore[assignment]

        strategy = MapReduceStrategy()
        ctx = StrategyContext(enable_consult=False)

        result = await strategy.execute(
            "task", {"agent1": a1, "agent2": a2}, ctx,
        )

        assert result.output
        assert len(consult_agents) == 0


class TestConsultMapReduceSingleAgent:
    """Map-reduce single-agent path bypasses consult."""

    @pytest.mark.asyncio
    async def test_single_agent_no_consult(self) -> None:
        """Single agent in map-reduce runs directly, no consult."""
        a1 = _make_real_agent("solo", response="Solo output")

        strategy = MapReduceStrategy()
        ctx = StrategyContext(enable_consult=True)

        result = await strategy.execute(
            "task", {"solo": a1}, ctx,
        )

        assert result.output == "Solo output"
        assert result.rounds == 1


# ===========================================================================
# AgentTeam parameter passthrough
# ===========================================================================


class TestTeamConsultParams:
    """Tests that AgentTeam passes consult params to StrategyContext."""

    def test_enable_consult_stored(self) -> None:
        """AgentTeam stores enable_consult."""
        a1 = _make_real_agent("agent1")
        team = AgentTeam(
            name="test-team",
            members=[a1],
            strategy="round_robin",
            enable_consult=True,
            max_consult_depth=2,
        )
        assert team._enable_consult is True
        assert team._max_consult_depth == 2

    def test_enable_consult_default_false(self) -> None:
        """Default enable_consult is False."""
        a1 = _make_real_agent("agent1")
        team = AgentTeam(name="test-team", members=[a1], strategy="round_robin")
        assert team._enable_consult is False
        assert team._max_consult_depth == 1

    @pytest.mark.asyncio
    async def test_team_passes_consult_to_strategy(self) -> None:
        """AgentTeam.run() passes enable_consult and max_consult_depth to StrategyContext."""
        a1 = _make_real_agent("agent1", response="output")
        a2 = _make_real_agent("agent2", response="output2")

        team = AgentTeam(
            name="consult-team",
            members=[a1, a2],
            strategy="round_robin",
            max_rounds=1,
            enable_consult=True,
            max_consult_depth=2,
        )

        result = await team.run("task")
        assert result.output  # should complete without error

    @pytest.mark.asyncio
    async def test_team_consult_lifecycle(self) -> None:
        """Team with consult enabled can be created, run, and closed."""
        a1 = _make_real_agent("a1", response="r1")
        a2 = _make_real_agent("a2", response="r2")

        async with AgentTeam(
            name="lifecycle-team",
            members=[a1, a2],
            strategy="round_robin",
            max_rounds=1,
            enable_consult=True,
        ) as team:
            result = await team.run("lifecycle test")
            assert result.output == "r2"

        assert team._closed is True
