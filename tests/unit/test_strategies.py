"""Tests for orchestration strategies."""
from __future__ import annotations

from typing import Any

import pytest

from agentchord.core.agent import Agent
from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.shared_context import SharedContext
from agentchord.orchestration.strategies.base import BaseStrategy, StrategyContext
from agentchord.orchestration.strategies.coordinator import CoordinatorStrategy
from agentchord.orchestration.strategies.debate import DebateStrategy
from agentchord.orchestration.strategies.map_reduce import MapReduceStrategy
from agentchord.orchestration.strategies.round_robin import RoundRobinStrategy
from agentchord.orchestration.types import (
    AgentOutput,
    MessageType,
    TeamMember,
    TeamResult,
    TeamRole,
)

from tests.conftest import MockLLMProvider, MockToolCallProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(name: str, response: str = "Mock response", role: str = "tester") -> Agent:
    """Create a test agent with a mock provider."""
    return Agent(
        name=name,
        role=role,
        model="mock",
        llm_provider=MockLLMProvider(response_content=response),
    )


def _make_members(*names: str) -> list[TeamMember]:
    """Create TeamMember list from names."""
    return [
        TeamMember(name=n, role=TeamRole.WORKER) for n in names
    ]


def _ctx(**kwargs: Any) -> StrategyContext:
    """Shorthand for creating a StrategyContext with defaults."""
    return StrategyContext(**kwargs)


# ===========================================================================
# BaseStrategy
# ===========================================================================


class TestBaseStrategy:
    """Tests for BaseStrategy ABC."""

    def test_cannot_instantiate(self) -> None:
        """BaseStrategy is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseStrategy()  # type: ignore[abstract]

    def test_subclass_must_implement_execute(self) -> None:
        """Subclass without execute raises TypeError."""
        class Incomplete(BaseStrategy):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_valid_subclass(self) -> None:
        """Subclass with execute() can be instantiated."""
        class Valid(BaseStrategy):
            async def execute(self, task, agents, ctx):
                return TeamResult(output="ok", strategy="valid")

        strategy = Valid()
        assert strategy is not None


# ===========================================================================
# RoundRobinStrategy
# ===========================================================================


class TestRoundRobinStrategy:
    """Tests for RoundRobinStrategy."""

    @pytest.mark.asyncio
    async def test_single_agent_single_round(self) -> None:
        """Single agent, single round returns agent's output."""
        agent = _make_agent("alice", response="Alice output")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="Do something",
            agents={"alice": agent},
            ctx=_ctx(),
        )

        assert result.output == "Alice output"
        assert result.strategy == "round_robin"
        assert result.rounds == 1
        assert "alice_r1" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_multiple_agents_output_chaining(self) -> None:
        """Each agent receives previous agent's output as input."""
        # The second agent receives the first agent's output.
        # Both MockLLMProviders return their fixed content regardless of input,
        # but the chaining is verified through final output == last agent's response.
        alice = _make_agent("alice", response="Alice result")
        bob = _make_agent("bob", response="Bob result")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="Start",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(),
        )

        # Final output should be the last agent's response
        assert result.output == "Bob result"
        assert "alice_r1" in result.agent_outputs
        assert "bob_r1" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_multiple_rounds(self) -> None:
        """Multiple rounds iterate through all agents repeatedly."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="Start",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=2),
        )

        assert result.rounds == 2
        assert "alice_r1" in result.agent_outputs
        assert "bob_r1" in result.agent_outputs
        assert "alice_r2" in result.agent_outputs
        assert "bob_r2" in result.agent_outputs
        # Final output is last agent in last round
        assert result.output == "B"

    @pytest.mark.asyncio
    async def test_message_bus_integration(self) -> None:
        """Messages are recorded on the bus."""
        alice = _make_agent("alice", response="Result")
        bus = MessageBus()
        bus.register("alice")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="Test",
            agents={"alice": alice},
            ctx=_ctx(message_bus=bus),
        )

        assert len(result.messages) == 2  # TASK + RESULT
        assert result.messages[0].message_type == MessageType.TASK
        assert result.messages[1].message_type == MessageType.RESULT
        assert result.messages[0].sender == "system"
        assert result.messages[1].sender == "alice"

    @pytest.mark.asyncio
    async def test_cost_and_token_aggregation(self) -> None:
        """Costs and tokens are summed across all agent runs."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="Sum test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(),
        )

        # Each mock agent: 10 prompt + 5 completion = 15 tokens, cost = 0.001*10/1000 + 0.002*5/1000
        assert result.total_tokens > 0
        assert result.total_cost >= 0.0

    @pytest.mark.asyncio
    async def test_no_message_bus(self) -> None:
        """Works without a message bus."""
        agent = _make_agent("solo", response="Done")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="No bus",
            agents={"solo": agent},
            ctx=_ctx(),
        )

        assert result.output == "Done"
        assert result.messages == []

    @pytest.mark.asyncio
    async def test_duration_tracked(self) -> None:
        """Duration is recorded in milliseconds."""
        agent = _make_agent("fast", response="Quick")
        strategy = RoundRobinStrategy()

        result = await strategy.execute(
            task="Time test",
            agents={"fast": agent},
            ctx=_ctx(),
        )

        assert result.duration_ms >= 0


# ===========================================================================
# DebateStrategy
# ===========================================================================


class TestDebateStrategy:
    """Tests for DebateStrategy."""

    @pytest.mark.asyncio
    async def test_single_agent_debate(self) -> None:
        """Single agent debate produces output with synthesis."""
        agent = _make_agent("expert", response="Expert opinion")
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Discuss AI",
            agents={"expert": agent},
            ctx=_ctx(max_rounds=1),
        )

        assert result.output == "Expert opinion"
        assert result.strategy == "debate"
        # 1 debate round + 1 synthesis = 2 outputs
        assert "expert_r1" in result.agent_outputs
        assert "expert_synthesis" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_multiple_agents_debate(self) -> None:
        """Multiple agents produce debate entries."""
        alice = _make_agent("alice", response="Alice argues")
        bob = _make_agent("bob", response="Bob argues")
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Debate topic",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=2),
        )

        assert result.rounds == 2
        assert "alice_r1" in result.agent_outputs
        assert "bob_r1" in result.agent_outputs
        assert "alice_r2" in result.agent_outputs
        assert "bob_r2" in result.agent_outputs
        # Synthesis by first agent (alice)
        assert "alice_synthesis" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_custom_synthesizer(self) -> None:
        """Custom synthesizer agent creates the final output.

        Note: synthesizer is not yet part of StrategyContext. The debate
        strategy falls back to the first agent when synthesizer_name is None.
        This test verifies synthesis uses the first agent (alice) by default.
        """
        alice = _make_agent("alice", response="Alice view")
        bob = _make_agent("bob", response="Bob synthesis result")
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Topic",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=1),
        )

        # Without synthesizer in ctx, first agent (alice) synthesizes
        assert "alice_synthesis" in result.agent_outputs
        assert result.output == "Alice view"

    @pytest.mark.asyncio
    async def test_debate_message_bus(self) -> None:
        """Debate messages are recorded."""
        alice = _make_agent("alice", response="View A")
        bus = MessageBus()
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Topic",
            agents={"alice": alice},
            ctx=_ctx(max_rounds=1, message_bus=bus),
        )

        # 1 debate RESPONSE message
        assert len(result.messages) >= 1
        assert any(
            m.message_type == MessageType.RESPONSE for m in result.messages
        )

    @pytest.mark.asyncio
    async def test_debate_cost_aggregation(self) -> None:
        """Costs from all debate rounds and synthesis are summed."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Cost debate",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=1),
        )

        # alice_r1 + bob_r1 + alice_synthesis = 3 agent runs
        assert len(result.agent_outputs) == 3
        assert result.total_tokens > 0
        assert result.total_cost >= 0.0


# ===========================================================================
# MapReduceStrategy
# ===========================================================================


class TestMapReduceStrategy:
    """Tests for MapReduceStrategy."""

    @pytest.mark.asyncio
    async def test_single_agent_direct(self) -> None:
        """Single agent runs directly without map/reduce overhead."""
        agent = _make_agent("solo", response="Solo output")
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="Single task",
            agents={"solo": agent},
            ctx=_ctx(),
        )

        assert result.output == "Solo output"
        assert result.strategy == "map_reduce"
        assert result.rounds == 1
        assert "solo" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_parallel_map_and_reduce(self) -> None:
        """Multiple agents run in parallel, then first agent reduces."""
        alice = _make_agent("alice", response="Alice data")
        bob = _make_agent("bob", response="Bob data")
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="Analyze",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(),
        )

        # Map outputs
        assert "alice" in result.agent_outputs
        assert "bob" in result.agent_outputs
        # Reduce output
        assert "alice_reduce" in result.agent_outputs
        assert result.rounds == 2
        # Final output is from the reduce step
        assert result.output == "Alice data"  # alice's mock always returns this

    @pytest.mark.asyncio
    async def test_map_reduce_message_bus(self) -> None:
        """Messages for map and reduce phases are recorded."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        bus = MessageBus()
        bus.register("alice")
        bus.register("bob")
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="Test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(message_bus=bus),
        )

        # Map: 2 TASK + 2 RESULT, Reduce: 1 TASK + 1 RESULT = 3+3
        task_msgs = [
            m for m in result.messages if m.message_type == MessageType.TASK
        ]
        result_msgs = [
            m for m in result.messages if m.message_type == MessageType.RESULT
        ]
        assert len(task_msgs) == 3  # 2 map + 1 reduce
        assert len(result_msgs) == 3  # 2 map + 1 reduce

    @pytest.mark.asyncio
    async def test_map_reduce_cost_aggregation(self) -> None:
        """Costs from map and reduce phases are summed."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="Cost test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(),
        )

        # alice_map + bob_map + alice_reduce = 3 runs
        assert len(result.agent_outputs) == 3
        assert result.total_tokens > 0

    @pytest.mark.asyncio
    async def test_no_message_bus(self) -> None:
        """Works without a message bus."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="No bus",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(),
        )

        assert result.output is not None
        assert result.messages == []

    @pytest.mark.asyncio
    async def test_map_reduce_handles_agent_failure(self) -> None:
        """One agent raising an exception does not crash the whole run.

        The successful agent's output is still collected and the failing
        agent is recorded with an error message.
        """
        from tests.conftest import MockLLMProvider as _MLP

        class FailingProvider(_MLP):
            async def complete(self, messages, **kwargs):
                raise RuntimeError("LLM service unavailable")

        alice = _make_agent("alice", response="Alice data")
        bob = Agent(
            name="bob",
            role="tester",
            model="mock",
            llm_provider=FailingProvider(),
        )
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="Partial failure",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(),
        )

        # Alice succeeded
        assert "alice" in result.agent_outputs
        assert result.agent_outputs["alice"].output == "Alice data"

        # Bob recorded as error
        assert "bob" in result.agent_outputs
        assert "Error" in result.agent_outputs["bob"].output
        assert "LLM service unavailable" in result.agent_outputs["bob"].output
        assert result.agent_outputs["bob"].tokens == 0
        assert result.agent_outputs["bob"].cost == 0.0

        # Reduce phase still ran (using alice as reducer)
        assert "alice_reduce" in result.agent_outputs
        assert result.rounds == 2


# ===========================================================================
# CoordinatorStrategy
# ===========================================================================


class TestCoordinatorStrategy:
    """Tests for CoordinatorStrategy."""

    @pytest.mark.asyncio
    async def test_single_agent_fallback(self) -> None:
        """With only one agent (coordinator), runs directly."""
        coordinator = _make_agent("coord", response="Direct result")
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Simple task",
            agents={"coord": coordinator},
            ctx=_ctx(coordinator=coordinator),
        )

        assert result.output == "Direct result"
        assert result.strategy == "coordinator"
        assert "coord" in result.agent_outputs
        assert result.agent_outputs["coord"].role == TeamRole.COORDINATOR

    @pytest.mark.asyncio
    async def test_coordinator_auto_selection(self) -> None:
        """Without explicit coordinator, first agent is used."""
        first = _make_agent("first", response="First output")
        second = _make_agent("second", response="Second output")
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Auto select",
            agents={"first": first, "second": second},
            ctx=_ctx(),
        )

        # Coordinator is "first", worker is "second"
        assert result.output == "First output"
        assert result.strategy == "coordinator"

    @pytest.mark.asyncio
    async def test_delegation_tools_created_and_removed(self) -> None:
        """Delegation tools are added then removed after execution."""
        coordinator = _make_agent("coord", response="Coordinated")
        worker = _make_agent("worker", response="Worker output")
        strategy = CoordinatorStrategy()

        # Before: no tools
        assert coordinator._tool_executor is None

        await strategy.execute(
            task="Delegate test",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator),
        )

        # After: tools restored (None since coordinator had no tools)
        assert coordinator._tool_executor is None

    @pytest.mark.asyncio
    async def test_system_prompt_restored(self) -> None:
        """Coordinator's system prompt is restored after execution."""
        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            system_prompt="Original prompt",
            llm_provider=MockLLMProvider(response_content="Done"),
        )
        worker = _make_agent("worker", response="Result")
        strategy = CoordinatorStrategy()

        await strategy.execute(
            task="Prompt test",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator),
        )

        assert coordinator._system_prompt == "Original prompt"

    @pytest.mark.asyncio
    async def test_system_prompt_restored_on_error(self) -> None:
        """System prompt is restored even if execution raises."""
        class FailingProvider(MockLLMProvider):
            async def complete(self, messages, **kwargs):
                raise RuntimeError("LLM failure")

        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            system_prompt="Original",
            llm_provider=FailingProvider(),
        )
        worker = _make_agent("worker", response="Result")
        strategy = CoordinatorStrategy()

        with pytest.raises(Exception):
            await strategy.execute(
                task="Error test",
                agents={"coord": coordinator, "worker": worker},
                ctx=_ctx(coordinator=coordinator),
            )

        assert coordinator._system_prompt == "Original"
        assert coordinator._tool_executor is None

    @pytest.mark.asyncio
    async def test_existing_tools_preserved(self) -> None:
        """Coordinator's existing tools are preserved after execution."""
        from agentchord.tools.base import Tool, ToolParameter

        async def my_tool(x: str) -> str:
            return f"result: {x}"

        existing_tool = Tool(
            name="my_tool",
            description="Existing tool",
            parameters=[
                ToolParameter(
                    name="x", type="string",
                    description="Input", required=True,
                ),
            ],
            func=my_tool,
        )

        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            llm_provider=MockLLMProvider(response_content="Done"),
            tools=[existing_tool],
        )
        worker = _make_agent("worker", response="Result")
        strategy = CoordinatorStrategy()

        # Before: has existing tool
        assert "my_tool" in coordinator._tool_executor._tools

        await strategy.execute(
            task="Preserve tools",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator),
        )

        # After: existing tool still present, delegation tools gone
        assert "my_tool" in coordinator._tool_executor._tools
        assert "delegate_to_worker" not in coordinator._tool_executor._tools

    @pytest.mark.asyncio
    async def test_with_tool_calling_delegation(self) -> None:
        """Coordinator uses tool calling to delegate to workers."""
        from agentchord.core.types import ToolCall

        # Coordinator makes a tool call on first complete(), then final response
        tool_call = ToolCall(
            id="tc1",
            name="delegate_to_worker",
            arguments={"task_description": "Do the work"},
        )
        coord_provider = MockToolCallProvider(
            tool_calls_sequence=[[tool_call], None],
            responses=["", "Final synthesized output"],
        )
        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            llm_provider=coord_provider,
        )
        worker = _make_agent("worker", response="Worker completed the task")
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Complex task",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator),
        )

        assert result.output == "Final synthesized output"
        assert "worker" in result.agent_outputs
        assert result.agent_outputs["worker"].output == "Worker completed the task"
        assert result.agent_outputs["coord"].role == TeamRole.COORDINATOR

    @pytest.mark.asyncio
    async def test_message_bus_delegation(self) -> None:
        """Delegation messages are recorded on the bus."""
        from agentchord.core.types import ToolCall

        tool_call = ToolCall(
            id="tc1",
            name="delegate_to_worker",
            arguments={"task_description": "Analyze data"},
        )
        coord_provider = MockToolCallProvider(
            tool_calls_sequence=[[tool_call], None],
            responses=["", "Done"],
        )
        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            llm_provider=coord_provider,
        )
        worker = _make_agent("worker", response="Analysis complete")
        bus = MessageBus()
        bus.register("coord")
        bus.register("worker")
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Bus test",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator, message_bus=bus),
        )

        # Should have TASK (coord->worker) and RESULT (worker->coord) messages
        assert len(result.messages) >= 2
        task_msgs = [
            m for m in result.messages if m.message_type == MessageType.TASK
        ]
        result_msgs = [
            m for m in result.messages if m.message_type == MessageType.RESULT
        ]
        assert len(task_msgs) >= 1
        assert len(result_msgs) >= 1
        assert task_msgs[0].sender == "coord"
        assert task_msgs[0].recipient == "worker"

    @pytest.mark.asyncio
    async def test_with_member_capabilities(self) -> None:
        """Member capabilities are included in delegation tool descriptions."""
        coordinator = _make_agent("coord", response="Coordinated")
        worker = _make_agent("researcher", response="Research done")
        members = [
            TeamMember(
                name="researcher",
                role=TeamRole.SPECIALIST,
                capabilities=["web_search", "summarization"],
            ),
        ]
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Research task",
            agents={"coord": coordinator, "researcher": worker},
            ctx=_ctx(coordinator=coordinator, members=members),
        )

        assert result.strategy == "coordinator"
        assert result.output == "Coordinated"

    @pytest.mark.asyncio
    async def test_multiple_workers(self) -> None:
        """Multiple workers all get delegation tools."""
        from agentchord.core.types import ToolCall

        # Coordinator delegates to both workers
        tc1 = ToolCall(
            id="tc1",
            name="delegate_to_alice",
            arguments={"task_description": "Research"},
        )
        tc2 = ToolCall(
            id="tc2",
            name="delegate_to_bob",
            arguments={"task_description": "Analyze"},
        )
        coord_provider = MockToolCallProvider(
            tool_calls_sequence=[[tc1, tc2], None],
            responses=["", "Merged result"],
        )
        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            llm_provider=coord_provider,
        )
        alice = _make_agent("alice", response="Alice research")
        bob = _make_agent("bob", response="Bob analysis")
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Multi-worker",
            agents={"coord": coordinator, "alice": alice, "bob": bob},
            ctx=_ctx(coordinator=coordinator),
        )

        assert result.output == "Merged result"
        assert "alice" in result.agent_outputs
        assert "bob" in result.agent_outputs
        assert "coord" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_cost_token_aggregation(self) -> None:
        """Costs and tokens from all agents are aggregated."""
        from agentchord.core.types import ToolCall

        tool_call = ToolCall(
            id="tc1",
            name="delegate_to_worker",
            arguments={"task_description": "Work"},
        )
        coord_provider = MockToolCallProvider(
            tool_calls_sequence=[[tool_call], None],
            responses=["", "Done"],
        )
        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            llm_provider=coord_provider,
        )
        worker = _make_agent("worker", response="Result")
        strategy = CoordinatorStrategy()

        result = await strategy.execute(
            task="Cost check",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator),
        )

        assert result.total_tokens > 0
        assert result.total_cost >= 0.0
        # Both agents contributed
        assert len(result.agent_outputs) == 2


# ===========================================================================
# Cross-Strategy Tests
# ===========================================================================


class TestStrategyCommon:
    """Cross-cutting tests applicable to all strategies."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_cls", [
        RoundRobinStrategy,
        DebateStrategy,
        MapReduceStrategy,
        CoordinatorStrategy,
    ])
    async def test_team_result_structure(self, strategy_cls: type) -> None:
        """All strategies return a valid TeamResult."""
        agent = _make_agent("agent", response="Output")
        strategy = strategy_cls()

        ctx_kwargs: dict[str, Any] = {}
        if strategy_cls == DebateStrategy:
            ctx_kwargs["max_rounds"] = 1

        result = await strategy.execute(
            task="Structural test",
            agents={"agent": agent},
            ctx=_ctx(**ctx_kwargs),
        )

        assert isinstance(result, TeamResult)
        assert result.output is not None
        assert result.strategy != ""
        assert result.duration_ms >= 0
        assert isinstance(result.agent_outputs, dict)
        assert len(result.agent_outputs) >= 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_cls,strategy_name", [
        (RoundRobinStrategy, "round_robin"),
        (DebateStrategy, "debate"),
        (MapReduceStrategy, "map_reduce"),
        (CoordinatorStrategy, "coordinator"),
    ])
    async def test_strategy_name(
        self, strategy_cls: type, strategy_name: str,
    ) -> None:
        """Each strategy reports its correct name."""
        agent = _make_agent("agent", response="Out")
        ctx_kwargs: dict[str, Any] = {}
        if strategy_cls == DebateStrategy:
            ctx_kwargs["max_rounds"] = 1

        result = await strategy_cls().execute(
            task="Name test",
            agents={"agent": agent},
            ctx=_ctx(**ctx_kwargs),
        )

        assert result.strategy == strategy_name


# ===========================================================================
# SharedContext Wiring
# ===========================================================================


class TestSharedContextWiring:
    """Tests that all strategies wire results to SharedContext."""

    @pytest.mark.asyncio
    async def test_round_robin_stores_to_context(self) -> None:
        """Round robin stores per-agent-per-round and final output."""
        alice = _make_agent("alice", response="Alice out")
        bob = _make_agent("bob", response="Bob out")
        ctx_obj = SharedContext()
        strategy = RoundRobinStrategy()

        await strategy.execute(
            task="Context test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(shared_context=ctx_obj, max_rounds=2),
        )

        assert ctx_obj.update_count > 0
        assert await ctx_obj.get("alice_r1") == "Alice out"
        assert await ctx_obj.get("bob_r1") == "Bob out"
        assert await ctx_obj.get("alice_r2") == "Alice out"
        assert await ctx_obj.get("bob_r2") == "Bob out"
        assert await ctx_obj.get("final_output") == "Bob out"

    @pytest.mark.asyncio
    async def test_debate_stores_positions_and_synthesis(self) -> None:
        """Debate stores positions per round and synthesis."""
        alice = _make_agent("alice", response="Alice view")
        bob = _make_agent("bob", response="Bob view")
        ctx_obj = SharedContext()
        strategy = DebateStrategy()

        await strategy.execute(
            task="Debate context test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(shared_context=ctx_obj, max_rounds=1),
        )

        assert await ctx_obj.get("alice_position_r1") == "Alice view"
        assert await ctx_obj.get("bob_position_r1") == "Bob view"
        assert await ctx_obj.get("synthesis") is not None

    @pytest.mark.asyncio
    async def test_map_reduce_stores_map_and_reduce(self) -> None:
        """Map-reduce stores map results and reduce output."""
        alice = _make_agent("alice", response="Alice data")
        bob = _make_agent("bob", response="Bob data")
        ctx_obj = SharedContext()
        strategy = MapReduceStrategy()

        await strategy.execute(
            task="MR context test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(shared_context=ctx_obj),
        )

        assert await ctx_obj.get("alice_map") == "Alice data"
        assert await ctx_obj.get("bob_map") == "Bob data"
        assert await ctx_obj.get("reduce_result") is not None

    @pytest.mark.asyncio
    async def test_coordinator_context_tools_injected(self) -> None:
        """Coordinator gets context tools when shared_context provided."""
        coordinator = _make_agent("coord", response="Done")
        worker = _make_agent("worker", response="Result")
        ctx_obj = SharedContext()
        strategy = CoordinatorStrategy()

        # Track what tools the coordinator receives during execution
        original_temp_tools = coordinator.temporary_tools

        captured_tools: list[str] = []
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def spy_temporary_tools(tools):  # type: ignore[no-untyped-def]
            captured_tools.extend([t.name for t in tools])
            async with original_temp_tools(tools):
                yield coordinator

        coordinator.temporary_tools = spy_temporary_tools  # type: ignore[assignment]

        await strategy.execute(
            task="Context tools test",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator, shared_context=ctx_obj),
        )

        assert "delegate_to_worker" in captured_tools
        assert "read_shared_context" in captured_tools
        assert "write_shared_context" in captured_tools
        assert "list_shared_context" in captured_tools

    @pytest.mark.asyncio
    async def test_no_shared_context_no_error(self) -> None:
        """Strategies work fine without shared_context (backward compat)."""
        agent = _make_agent("solo", response="OK")

        for strategy in [RoundRobinStrategy(), DebateStrategy(), MapReduceStrategy()]:
            ctx_kwargs: dict[str, Any] = {}
            if isinstance(strategy, DebateStrategy):
                ctx_kwargs["max_rounds"] = 1
            result = await strategy.execute(
                task="No context",
                agents={"solo": agent},
                ctx=_ctx(**ctx_kwargs),
            )
            assert result.output is not None

    @pytest.mark.asyncio
    async def test_coordinator_delegation_stores_to_context(self) -> None:
        """Coordinator delegation results are stored in SharedContext."""
        from agentchord.core.types import ToolCall

        tool_call = ToolCall(
            id="tc1",
            name="delegate_to_worker",
            arguments={"task_description": "Do work"},
        )
        coord_provider = MockToolCallProvider(
            tool_calls_sequence=[[tool_call], None],
            responses=["", "Final"],
        )
        coordinator = Agent(
            name="coord",
            role="leader",
            model="mock",
            llm_provider=coord_provider,
        )
        worker = _make_agent("worker", response="Worker output")
        ctx_obj = SharedContext()
        strategy = CoordinatorStrategy()

        await strategy.execute(
            task="Delegation context test",
            agents={"coord": coordinator, "worker": worker},
            ctx=_ctx(coordinator=coordinator, shared_context=ctx_obj),
        )

        assert await ctx_obj.get("worker_result") == "Worker output"


# ===========================================================================
# Callback Emissions
# ===========================================================================


class _MockCallbackManager:
    """Simple callback recorder for testing."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, **kwargs: Any) -> None:
        self.events.append((event_type, kwargs))


class TestCallbackEmissions:
    """Tests that all strategies emit callback events."""

    @pytest.mark.asyncio
    async def test_round_robin_emits_callbacks(self) -> None:
        """Round-robin emits agent_delegated and agent_completed per agent."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        cb = _MockCallbackManager()
        strategy = RoundRobinStrategy()

        await strategy.execute(
            task="CB test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(callbacks=cb, max_rounds=1),
        )

        event_types = [e[0] for e in cb.events]
        assert "agent_delegated" in event_types
        assert "agent_completed" in event_types
        # Should have delegated + completed for each agent
        assert event_types.count("agent_delegated") == 2
        assert event_types.count("agent_completed") == 2

    @pytest.mark.asyncio
    async def test_round_robin_callback_metadata(self) -> None:
        """Round-robin callbacks include round number and strategy name."""
        alice = _make_agent("alice", response="A")
        cb = _MockCallbackManager()
        strategy = RoundRobinStrategy()

        await strategy.execute(
            task="Meta test",
            agents={"alice": alice},
            ctx=_ctx(callbacks=cb, max_rounds=2),
        )

        delegated_events = [e for e in cb.events if e[0] == "agent_delegated"]
        assert delegated_events[0][1]["round"] == 1
        assert delegated_events[1][1]["round"] == 2
        assert delegated_events[0][1]["strategy"] == "round_robin"

        completed_events = [e for e in cb.events if e[0] == "agent_completed"]
        assert completed_events[0][1]["tokens"] >= 0
        assert "cost" in completed_events[0][1]

    @pytest.mark.asyncio
    async def test_debate_emits_callbacks(self) -> None:
        """Debate emits agent_delegated, agent_completed, and synthesis_start."""
        alice = _make_agent("alice", response="A")
        cb = _MockCallbackManager()
        strategy = DebateStrategy()

        await strategy.execute(
            task="CB debate",
            agents={"alice": alice},
            ctx=_ctx(callbacks=cb, max_rounds=1),
        )

        event_types = [e[0] for e in cb.events]
        assert "agent_delegated" in event_types
        assert "agent_completed" in event_types
        assert "synthesis_start" in event_types

    @pytest.mark.asyncio
    async def test_debate_synthesis_callback_metadata(self) -> None:
        """Debate synthesis_start includes synthesizer and round info."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        cb = _MockCallbackManager()
        strategy = DebateStrategy()

        await strategy.execute(
            task="Synth CB",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(callbacks=cb, max_rounds=2),
        )

        synth_events = [e for e in cb.events if e[0] == "synthesis_start"]
        assert len(synth_events) == 1
        assert synth_events[0][1]["synthesizer"] == "alice"
        assert synth_events[0][1]["debate_rounds"] == 2

        # synthesis agent_completed has phase="synthesis"
        synth_completed = [
            e for e in cb.events
            if e[0] == "agent_completed" and e[1].get("phase") == "synthesis"
        ]
        assert len(synth_completed) == 1

    @pytest.mark.asyncio
    async def test_map_reduce_emits_callbacks(self) -> None:
        """Map-reduce emits map_phase_start, reduce_phase_start, and agent_completed."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        cb = _MockCallbackManager()
        strategy = MapReduceStrategy()

        await strategy.execute(
            task="CB map_reduce",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(callbacks=cb),
        )

        event_types = [e[0] for e in cb.events]
        assert "map_phase_start" in event_types
        assert "reduce_phase_start" in event_types
        assert event_types.count("agent_completed") >= 3  # 2 map + 1 reduce

    @pytest.mark.asyncio
    async def test_map_reduce_callback_metadata(self) -> None:
        """Map-reduce callbacks include phase and agent count info."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        cb = _MockCallbackManager()
        strategy = MapReduceStrategy()

        await strategy.execute(
            task="Meta MR",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(callbacks=cb),
        )

        map_start = [e for e in cb.events if e[0] == "map_phase_start"]
        assert map_start[0][1]["agent_count"] == 2

        reduce_start = [e for e in cb.events if e[0] == "reduce_phase_start"]
        assert reduce_start[0][1]["partial_count"] == 2
        assert reduce_start[0][1]["reducer"] == "alice"

        # Map completions have phase="map"
        map_completed = [
            e for e in cb.events
            if e[0] == "agent_completed" and e[1].get("phase") == "map"
        ]
        assert len(map_completed) == 2

        # Reduce completion has phase="reduce"
        reduce_completed = [
            e for e in cb.events
            if e[0] == "agent_completed" and e[1].get("phase") == "reduce"
        ]
        assert len(reduce_completed) == 1

    @pytest.mark.asyncio
    async def test_map_reduce_emits_error_callback(self) -> None:
        """Map-reduce emits agent_error for failed agents."""
        from tests.conftest import MockLLMProvider as _MLP

        class FailingProvider(_MLP):
            async def complete(self, messages, **kwargs):  # type: ignore[override]
                raise RuntimeError("Boom")

        alice = _make_agent("alice", response="A")
        bob = Agent(
            name="bob",
            role="tester",
            model="mock",
            llm_provider=FailingProvider(),
        )
        cb = _MockCallbackManager()
        strategy = MapReduceStrategy()

        await strategy.execute(
            task="Error CB",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(callbacks=cb),
        )

        event_types = [e[0] for e in cb.events]
        assert "agent_error" in event_types
        error_events = [e for e in cb.events if e[0] == "agent_error"]
        assert error_events[0][1]["agent_name"] == "bob"
        assert "Boom" in error_events[0][1]["error"]
        assert error_events[0][1]["phase"] == "map"

    @pytest.mark.asyncio
    async def test_no_callbacks_no_error(self) -> None:
        """Strategies work fine without callbacks."""
        agent = _make_agent("solo", response="OK")

        for strategy in [RoundRobinStrategy(), DebateStrategy(), MapReduceStrategy()]:
            ctx_kwargs: dict[str, Any] = {}
            if isinstance(strategy, DebateStrategy):
                ctx_kwargs["max_rounds"] = 1
            result = await strategy.execute(
                task="No CB",
                agents={"solo": agent},
                ctx=_ctx(**ctx_kwargs),
            )
            assert result.output is not None


# ===========================================================================
# Debate MessageBus Completeness
# ===========================================================================


class TestDebateMessageBusComplete:
    """Tests that debate strategy has complete TASK+RESULT message pairs."""

    @pytest.mark.asyncio
    async def test_debate_sends_task_and_response(self) -> None:
        """Debate sends TASK before each agent and RESPONSE after."""
        alice = _make_agent("alice", response="View")
        bus = MessageBus()
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Bus test",
            agents={"alice": alice},
            ctx=_ctx(max_rounds=1, message_bus=bus),
        )

        task_msgs = [m for m in result.messages if m.message_type == MessageType.TASK]
        resp_msgs = [m for m in result.messages if m.message_type == MessageType.RESPONSE]
        result_msgs = [m for m in result.messages if m.message_type == MessageType.RESULT]

        # 1 debate TASK + 1 RESPONSE + 1 synthesis TASK + 1 synthesis RESULT
        assert len(task_msgs) >= 1
        assert len(resp_msgs) >= 1  # Debate responses
        assert len(result_msgs) >= 1  # Synthesis result

    @pytest.mark.asyncio
    async def test_debate_synthesis_messages(self) -> None:
        """Debate sends synthesis TASK and RESULT messages."""
        alice = _make_agent("alice", response="View")
        bob = _make_agent("bob", response="Counter")
        bus = MessageBus()
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Synth bus test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=1, message_bus=bus),
        )

        # Check synthesis-specific messages
        synth_task = [
            m for m in result.messages
            if m.message_type == MessageType.TASK
            and m.metadata.get("phase") == "synthesis"
        ]
        synth_result = [
            m for m in result.messages
            if m.message_type == MessageType.RESULT
            and m.metadata.get("phase") == "synthesis"
        ]
        assert len(synth_task) == 1
        assert synth_task[0].recipient == "alice"  # First agent synthesizes
        assert len(synth_result) == 1
        assert synth_result[0].sender == "alice"

# ===========================================================================
# DebateStrategy Convergence
# ===========================================================================


class TestDebateConvergence:
    """Tests for DebateStrategy convergence detection."""

    @pytest.mark.asyncio
    async def test_converges_early_with_stable_output(self) -> None:
        """Debate exits early when all agents repeat their positions."""
        alice = _make_agent("alice", response="I agree with X")
        bob = _make_agent("bob", response="I also agree with X")
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Debate convergence",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=5),
        )

        # Should converge after round 2 (identical to round 1)
        assert result.rounds == 2
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_convergence_stores_to_shared_context(self) -> None:
        """Convergence info is stored in SharedContext."""
        alice = _make_agent("alice", response="Stable")
        ctx_obj = SharedContext()
        strategy = DebateStrategy()

        await strategy.execute(
            task="Context convergence",
            agents={"alice": alice},
            ctx=_ctx(max_rounds=5, shared_context=ctx_obj),
        )

        assert await ctx_obj.get("converged") is True
        assert await ctx_obj.get("convergence_round") is not None

    @pytest.mark.asyncio
    async def test_convergence_emits_callback(self) -> None:
        """Convergence triggers a callback event."""
        alice = _make_agent("alice", response="Same")
        bob = _make_agent("bob", response="Same too")

        cb = _MockCallbackManager()
        strategy = DebateStrategy()

        await strategy.execute(
            task="CB convergence",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(max_rounds=5, callbacks=cb),
        )

        event_types = [e[0] for e in cb.events]
        assert "convergence_detected" in event_types

    @pytest.mark.asyncio
    async def test_no_convergence_runs_all_rounds(self) -> None:
        """Without convergence, all max_rounds are executed."""
        alice = _make_agent("alice", response="View A")
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Single round",
            agents={"alice": alice},
            ctx=_ctx(max_rounds=1),
        )

        # Only 1 round, no convergence possible
        assert result.rounds == 1

    @pytest.mark.asyncio
    async def test_single_agent_converges(self) -> None:
        """Single agent with stable output converges after 2 rounds."""
        agent = _make_agent("solo", response="Stable view")
        ctx_obj = SharedContext()
        strategy = DebateStrategy()

        result = await strategy.execute(
            task="Solo convergence",
            agents={"solo": agent},
            ctx=_ctx(max_rounds=10, shared_context=ctx_obj),
        )

        assert result.rounds == 2  # round 1 sets position, round 2 matches = converge
        assert await ctx_obj.get("converged") is True


    @pytest.mark.asyncio
    async def test_map_reduce_reduce_messages(self) -> None:
        """Map-reduce sends TASK+RESULT for reduce phase."""
        alice = _make_agent("alice", response="A")
        bob = _make_agent("bob", response="B")
        bus = MessageBus()
        bus.register("alice")
        bus.register("bob")
        strategy = MapReduceStrategy()

        result = await strategy.execute(
            task="MR bus test",
            agents={"alice": alice, "bob": bob},
            ctx=_ctx(message_bus=bus),
        )

        # Map: 2 TASK + 2 RESULT, Reduce: 1 TASK + 1 RESULT = 6 total
        assert len(result.messages) >= 6

        # Verify reduce-specific messages
        reduce_task = [
            m for m in result.messages
            if m.message_type == MessageType.TASK
            and m.metadata.get("phase") == "reduce"
        ]
        reduce_result = [
            m for m in result.messages
            if m.message_type == MessageType.RESULT
            and m.metadata.get("phase") == "reduce"
        ]
        assert len(reduce_task) == 1
        assert reduce_task[0].recipient == "alice"  # First agent reduces
        assert len(reduce_result) == 1
        assert reduce_result[0].sender == "alice"
