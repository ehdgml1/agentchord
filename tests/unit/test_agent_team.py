"""Unit tests for AgentTeam orchestration class."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agentweave.core.agent import Agent
from agentweave.orchestration.message_bus import MessageBus
from agentweave.orchestration.shared_context import SharedContext
from agentweave.orchestration.team import AgentTeam
from agentweave.orchestration.types import (
    OrchestrationStrategy,
    TeamEvent,
    TeamMember,
    TeamResult,
    TeamRole,
)
from agentweave.tracking.callbacks import CallbackManager

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


class TestAgentTeamCreation:
    """Tests for AgentTeam initialization."""

    def test_create_team_with_agents(self) -> None:
        """AgentTeam accepts Agent instances directly."""
        a1 = _make_agent("agent-1")
        a2 = _make_agent("agent-2")
        team = AgentTeam(name="test-team", members=[a1, a2])

        assert team.name == "test-team"
        assert len(team.members) == 2
        assert "agent-1" in team.agents
        assert "agent-2" in team.agents

    def test_create_team_with_team_members(self) -> None:
        """AgentTeam accepts TeamMember descriptors."""
        tm1 = TeamMember(name="member-1", role=TeamRole.SPECIALIST)
        tm2 = TeamMember(name="member-2", role=TeamRole.REVIEWER)
        team = AgentTeam(name="test-team", members=[tm1, tm2])

        assert len(team.members) == 2
        assert team.members[0].role == TeamRole.SPECIALIST
        assert team.members[1].role == TeamRole.REVIEWER
        # TeamMember descriptors don't auto-create agents
        assert len(team.agents) == 0

    def test_create_team_invalid_member_raises(self) -> None:
        """AgentTeam raises TypeError for invalid member types."""
        with pytest.raises(TypeError, match="Expected Agent or TeamMember"):
            AgentTeam(name="bad-team", members=["not-an-agent"])

    def test_create_team_invalid_member_dict_raises(self) -> None:
        """AgentTeam raises TypeError for dict members."""
        with pytest.raises(TypeError, match="Expected Agent or TeamMember"):
            AgentTeam(name="bad-team", members=[{"name": "x"}])


class TestAgentTeamProperties:
    """Tests for AgentTeam properties."""

    def test_team_properties(self) -> None:
        """All properties return correct values."""
        a1 = _make_agent("agent-1")
        ctx = SharedContext()
        bus = MessageBus()
        team = AgentTeam(
            name="my-team",
            members=[a1],
            strategy="round_robin",
            shared_context=ctx,
            message_bus=bus,
        )

        assert team.name == "my-team"
        assert team.strategy == "round_robin"
        assert team.shared_context is ctx
        assert team.message_bus is bus
        assert len(team.members) == 1
        assert team.members[0].name == "agent-1"
        assert "agent-1" in team.agents

    def test_strategy_from_enum(self) -> None:
        """Strategy can be specified as enum."""
        a1 = _make_agent("agent-1")
        team = AgentTeam(
            name="enum-team",
            members=[a1],
            strategy=OrchestrationStrategy.DEBATE,
        )
        assert team.strategy == "debate"

    def test_coordinator_registered(self) -> None:
        """Coordinator agent is registered in agents dict."""
        worker = _make_agent("worker")
        coord = _make_agent("coordinator")
        team = AgentTeam(
            name="coord-team",
            members=[worker],
            coordinator=coord,
        )
        assert "coordinator" in team.agents
        assert "worker" in team.agents

    def test_repr(self) -> None:
        """repr returns informative string."""
        a1 = _make_agent("a1")
        team = AgentTeam(name="repr-team", members=[a1])
        rep = repr(team)
        assert "repr-team" in rep
        assert "1" in rep  # member count
        assert "coordinator" in rep  # strategy name


class TestAgentTeamStrategies:
    """Tests for running teams with different strategies."""

    @pytest.mark.asyncio
    async def test_run_coordinator_strategy(self) -> None:
        """Coordinator strategy delegates to workers via tool calls."""
        # For coordinator strategy: coordinator + workers
        # The coordinator's LLM must produce tool calls to delegate.
        # With MockLLMProvider (no tool calls), it just runs directly.
        coord = _make_agent("coord", response="Coordinated result")
        worker = _make_agent("worker", response="Worker output")
        team = AgentTeam(
            name="coord-team",
            members=[worker],
            coordinator=coord,
            strategy="coordinator",
        )

        result = await team.run("Test task")
        assert isinstance(result, TeamResult)
        assert result.output  # Has output
        assert result.team_name == "coord-team"
        assert result.strategy == "coordinator"
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_round_robin_strategy(self) -> None:
        """Round-robin strategy runs agents sequentially."""
        a1 = _make_agent("first", response="First pass")
        a2 = _make_agent("second", response="Second pass")
        team = AgentTeam(
            name="rr-team",
            members=[a1, a2],
            strategy="round_robin",
            max_rounds=1,
        )

        result = await team.run("Sequential task")
        assert isinstance(result, TeamResult)
        assert result.output == "Second pass"  # Last agent's output
        assert result.strategy == "round_robin"
        assert result.total_tokens > 0
        assert result.rounds == 1

    @pytest.mark.asyncio
    async def test_run_debate_strategy(self) -> None:
        """Debate strategy runs agents in debate rounds + synthesis."""
        a1 = _make_agent("debater-a", response="Position A")
        a2 = _make_agent("debater-b", response="Position B")
        team = AgentTeam(
            name="debate-team",
            members=[a1, a2],
            strategy="debate",
            max_rounds=2,
        )

        result = await team.run("Debate topic")
        assert isinstance(result, TeamResult)
        assert result.strategy == "debate"
        assert result.rounds == 2
        # Should have outputs from both debaters + synthesis
        assert len(result.agent_outputs) >= 2

    @pytest.mark.asyncio
    async def test_run_map_reduce_strategy(self) -> None:
        """Map-reduce strategy runs agents in parallel then merges."""
        a1 = _make_agent("mapper-1", response="Map result 1")
        a2 = _make_agent("mapper-2", response="Map result 2")
        a3 = _make_agent("mapper-3", response="Map result 3")
        team = AgentTeam(
            name="mr-team",
            members=[a1, a2, a3],
            strategy="map_reduce",
        )

        result = await team.run("Map-reduce task")
        assert isinstance(result, TeamResult)
        assert result.strategy == "map_reduce"
        assert result.rounds == 2  # map + reduce
        assert result.total_tokens > 0

    @pytest.mark.asyncio
    async def test_run_sequential_strategy_alias(self) -> None:
        """Sequential strategy is an alias for round_robin."""
        a1 = _make_agent("step-1", response="Step 1 done")
        a2 = _make_agent("step-2", response="Step 2 done")
        team = AgentTeam(
            name="seq-team",
            members=[a1, a2],
            strategy="sequential",
            max_rounds=1,
        )

        result = await team.run("Sequential task")
        assert result.output == "Step 2 done"
        assert result.strategy == "sequential"  # Should match input name


class TestAgentTeamSync:
    """Tests for synchronous execution."""

    def test_run_sync(self) -> None:
        """run_sync works in non-async context."""
        a1 = _make_agent("sync-agent", response="Sync result")
        team = AgentTeam(
            name="sync-team",
            members=[a1],
            strategy="round_robin",
            max_rounds=1,
        )

        result = team.run_sync("Sync task")
        assert isinstance(result, TeamResult)
        assert result.output == "Sync result"


class TestAgentTeamStream:
    """Tests for streaming execution."""

    @pytest.mark.asyncio
    async def test_stream_yields_events(self) -> None:
        """stream() yields TeamEvent instances."""
        a1 = _make_agent("stream-agent", response="Streamed")
        team = AgentTeam(
            name="stream-team",
            members=[a1],
            strategy="round_robin",
            max_rounds=1,
        )

        events: list[TeamEvent] = []
        async for event in team.stream("Stream task"):
            events.append(event)

        assert len(events) >= 2  # At least team_start + team_complete
        assert events[0].type == "team_start"
        assert events[-1].type == "team_complete"
        assert events[-1].content == "Streamed"

    @pytest.mark.asyncio
    async def test_stream_contains_agent_results(self) -> None:
        """stream() includes agent_result events."""
        a1 = _make_agent("agent-a", response="Result A")
        a2 = _make_agent("agent-b", response="Result B")
        team = AgentTeam(
            name="stream-team-2",
            members=[a1, a2],
            strategy="round_robin",
            max_rounds=1,
        )

        events: list[TeamEvent] = []
        async for event in team.stream("Multi-agent task"):
            events.append(event)

        event_types = [e.type for e in events]
        assert "agent_result" in event_types
        assert "team_complete" in event_types


class TestAgentTeamErrors:
    """Tests for error handling."""

    def test_unknown_strategy_raises(self) -> None:
        """Unknown strategy name raises ValueError."""
        a1 = _make_agent("agent")
        with pytest.raises(ValueError, match="Unknown strategy 'nonexistent'"):
            AgentTeam(
                name="bad-strategy",
                members=[a1],
                strategy="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_run_after_close_raises(self) -> None:
        """Running a closed team raises RuntimeError."""
        a1 = _make_agent("agent")
        team = AgentTeam(name="close-test", members=[a1])
        await team.close()

        with pytest.raises(RuntimeError, match="AgentTeam has been closed"):
            await team.run("Should fail")

    @pytest.mark.asyncio
    async def test_stream_after_close_raises(self) -> None:
        """Streaming a closed team raises RuntimeError."""
        a1 = _make_agent("agent")
        team = AgentTeam(name="close-stream", members=[a1])
        await team.close()

        with pytest.raises(RuntimeError, match="AgentTeam has been closed"):
            async for _ in team.stream("Should fail"):
                pass


class TestAgentTeamLifecycle:
    """Tests for lifecycle management."""

    @pytest.mark.asyncio
    async def test_close_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        a1 = _make_agent("agent")
        team = AgentTeam(name="idempotent", members=[a1])

        await team.close()
        await team.close()  # Should not raise
        assert team._closed is True

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """AgentTeam works as async context manager."""
        a1 = _make_agent("agent", response="Context result")

        async with AgentTeam(
            name="ctx-team",
            members=[a1],
            strategy="round_robin",
            max_rounds=1,
        ) as team:
            result = await team.run("Context task")
            assert result.output == "Context result"

        # After exiting, team should be closed
        assert team._closed is True


class TestAgentTeamCallbacks:
    """Tests for callback integration."""

    @pytest.mark.asyncio
    async def test_callbacks_emitted(self) -> None:
        """Callbacks are emitted during team execution."""
        emitted: list[str] = []

        async def _track(ctx: Any) -> None:
            emitted.append(str(ctx.event) if hasattr(ctx, "event") else str(ctx))

        cb = CallbackManager()
        cb.register_global(_track)

        a1 = _make_agent("agent", response="Callback result")
        team = AgentTeam(
            name="cb-team",
            members=[a1],
            strategy="round_robin",
            max_rounds=1,
            callbacks=cb,
        )

        await team.run("Callback task")
        # Should have emitted orchestration_start and orchestration_end at minimum
        event_strings = " ".join(emitted)
        assert "orchestration_start" in event_strings
        assert "orchestration_end" in event_strings


class TestAgentTeamResultMetadata:
    """Tests for TeamResult metadata population."""

    @pytest.mark.asyncio
    async def test_team_result_has_metadata(self) -> None:
        """TeamResult includes team_name, strategy, and duration_ms."""
        a1 = _make_agent("meta-agent", response="Metadata test")
        team = AgentTeam(
            name="meta-team",
            members=[a1],
            strategy="round_robin",
            max_rounds=1,
        )

        result = await team.run("Metadata task")
        assert result.team_name == "meta-team"
        assert result.strategy == "round_robin"
        assert result.duration_ms >= 0
        assert result.total_tokens >= 0
        assert result.total_cost >= 0.0

    @pytest.mark.asyncio
    async def test_team_result_has_messages(self) -> None:
        """TeamResult includes message bus history."""
        a1 = _make_agent("msg-agent", response="Message test")
        team = AgentTeam(
            name="msg-team",
            members=[a1],
            strategy="round_robin",
            max_rounds=1,
        )

        result = await team.run("Message task")
        # Round-robin sends TASK and RESULT messages via bus
        assert len(result.messages) >= 2
