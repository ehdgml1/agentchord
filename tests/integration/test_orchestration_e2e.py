"""End-to-end integration tests for AgentTeam orchestration."""
from __future__ import annotations

from typing import Any

import pytest

from agentchord.core.agent import Agent
from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.shared_context import SharedContext
from agentchord.orchestration.team import AgentTeam
from agentchord.orchestration.types import (
    TeamMember,
    TeamResult,
    TeamRole,
)

from tests.conftest import MockLLMProvider


def _make_agent(name: str, response: str = "Mock response") -> Agent:
    """Create an Agent with a MockLLMProvider."""
    provider = MockLLMProvider(response_content=response)
    return Agent(
        name=name,
        role=f"{name} role",
        model="mock-model",
        llm_provider=provider,
    )


class TestFullCoordinatorWorkflow:
    """E2E test for coordinator strategy with 3 agents."""

    @pytest.mark.asyncio
    async def test_full_coordinator_workflow(self) -> None:
        """Coordinator strategy runs coordinator + workers end-to-end.

        With MockLLMProvider (no tool calls), the coordinator just runs once.
        We verify the full pipeline: team creation -> execution -> result.
        """
        coordinator = _make_agent("coordinator", response="Coordinated output")
        researcher = _make_agent("researcher", response="Research findings")
        writer = _make_agent("writer", response="Written content")

        bus = MessageBus()
        bus.register("coordinator")
        bus.register("researcher")
        bus.register("writer")

        team = AgentTeam(
            name="full-coord-team",
            members=[researcher, writer],
            coordinator=coordinator,
            strategy="coordinator",
            message_bus=bus,
        )

        result = await team.run("Write a blog post about AI")

        assert isinstance(result, TeamResult)
        assert result.team_name == "full-coord-team"
        assert result.strategy == "coordinator"
        assert result.output  # Non-empty output
        assert result.duration_ms >= 0
        # Coordinator ran (even if no delegation happened due to mock)
        assert "coordinator" in result.agent_outputs


class TestFullDebateWorkflow:
    """E2E test for debate strategy with 2 agents, 2 rounds."""

    @pytest.mark.asyncio
    async def test_full_debate_workflow(self) -> None:
        """Debate strategy runs 2 agents for 2 rounds + synthesis."""
        optimist = _make_agent("optimist", response="AI is beneficial")
        pessimist = _make_agent("pessimist", response="AI has risks")

        bus = MessageBus()
        team = AgentTeam(
            name="debate-e2e",
            members=[optimist, pessimist],
            strategy="debate",
            message_bus=bus,
            max_rounds=2,
        )

        result = await team.run("Is AI beneficial for society?")

        assert isinstance(result, TeamResult)
        assert result.strategy == "debate"
        assert result.rounds == 2
        # 2 agents * 2 rounds + 1 synthesis = 5 agent outputs
        assert len(result.agent_outputs) == 5
        assert result.total_tokens > 0
        assert result.total_cost >= 0.0
        # Messages recorded in bus
        assert bus.message_count > 0


class TestFullMapReduceWorkflow:
    """E2E test for map-reduce strategy with 3 agents."""

    @pytest.mark.asyncio
    async def test_full_map_reduce_workflow(self) -> None:
        """Map-reduce runs 3 agents in parallel + reduce phase."""
        analyst_1 = _make_agent("analyst-1", response="Analysis from perspective 1")
        analyst_2 = _make_agent("analyst-2", response="Analysis from perspective 2")
        analyst_3 = _make_agent("analyst-3", response="Analysis from perspective 3")

        bus = MessageBus()
        team = AgentTeam(
            name="mr-e2e",
            members=[analyst_1, analyst_2, analyst_3],
            strategy="map_reduce",
            message_bus=bus,
        )

        result = await team.run("Analyze market trends")

        assert isinstance(result, TeamResult)
        assert result.strategy == "map_reduce"
        assert result.rounds == 2  # map + reduce
        # 3 map outputs + 1 reduce output = 4
        assert len(result.agent_outputs) == 4
        assert result.total_tokens > 0
        # Messages: 3 map TASK + 3 map RESULT + 1 reduce TASK + 1 reduce RESULT = 8
        assert bus.message_count == 8


class TestTeamWithSharedContext:
    """E2E test verifying shared context is accessible across execution."""

    @pytest.mark.asyncio
    async def test_team_with_shared_context(self) -> None:
        """Shared context is available and retains state."""
        ctx = SharedContext(initial={"topic": "AI agents"})
        a1 = _make_agent("agent-1", response="Agent 1 done")
        a2 = _make_agent("agent-2", response="Agent 2 done")

        team = AgentTeam(
            name="ctx-team",
            members=[a1, a2],
            strategy="round_robin",
            shared_context=ctx,
            max_rounds=1,
        )

        # Verify context is accessible before run
        assert team.shared_context is ctx
        topic = await ctx.get("topic")
        assert topic == "AI agents"

        result = await team.run("Work with shared context")
        assert result.output == "Agent 2 done"

        # Context should still be intact after execution
        topic_after = await ctx.get("topic")
        assert topic_after == "AI agents"

        # We can write to context and it persists
        await ctx.set("status", "completed", agent="test")
        status = await ctx.get("status")
        assert status == "completed"


class TestTeamWithMessageBus:
    """E2E test verifying message bus records agent communication."""

    @pytest.mark.asyncio
    async def test_team_with_message_bus(self) -> None:
        """Message bus records all agent communication."""
        bus = MessageBus()
        a1 = _make_agent("sender", response="Sent message")
        a2 = _make_agent("receiver", response="Received message")

        team = AgentTeam(
            name="bus-team",
            members=[a1, a2],
            strategy="round_robin",
            message_bus=bus,
            max_rounds=1,
        )

        result = await team.run("Test message passing")

        # Round-robin sends TASK and RESULT for each agent
        assert bus.message_count >= 4  # 2 agents * (1 TASK + 1 RESULT)
        history = bus.get_history()

        # Verify message structure
        senders = {msg.sender for msg in history}
        assert "sender" in senders or "system" in senders

        # Verify messages are also in result
        assert len(result.messages) == bus.message_count

    @pytest.mark.asyncio
    async def test_team_message_bus_agent_filter(self) -> None:
        """Message bus can filter messages by agent name."""
        bus = MessageBus()
        a1 = _make_agent("alpha", response="Alpha result")
        a2 = _make_agent("beta", response="Beta result")

        team = AgentTeam(
            name="filter-team",
            members=[a1, a2],
            strategy="round_robin",
            message_bus=bus,
            max_rounds=1,
        )

        await team.run("Filter test")

        alpha_msgs = bus.get_agent_messages("alpha")
        beta_msgs = bus.get_agent_messages("beta")

        # Each agent should have messages (sent or received)
        assert len(alpha_msgs) >= 1
        assert len(beta_msgs) >= 1
