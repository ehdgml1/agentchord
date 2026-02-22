"""Tests for multi-agent execution handler.

Tests cover:
- Multi-agent node routing in _execute_node
- Mock mode output structure
- Empty members edge case
- Node type routing validation
- Role mapping to TeamRole enum (P2-5)
- Capabilities passed to TeamMember (P2-4)
- coordinatorId support (P2-3)
- costBudget enforcement and budgetExceeded flag (P2-2)
- Per-agent event collection for SSE (P2-1)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.executor import (
    WorkflowExecutor,
    WorkflowNode,
    WorkflowEdge,
    Workflow,
    ExecutionStatus,
    ExecutionStateStore,
    _MultiAgentEventCollector,
)
from app.core.mcp_manager import MCPManager
from app.core.secret_store import SecretStore


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager."""
    return MCPManager()


@pytest.fixture
def mock_secret_store():
    """Mock secret store."""
    class MockDB:
        async def execute(self, *args, **kwargs):
            pass
        async def fetchone(self, *args, **kwargs):
            return None
        async def fetchall(self, *args, **kwargs):
            return []
    return SecretStore(MockDB())


@pytest.fixture
def mock_state_store():
    """Mock state store."""
    class MockDB:
        async def execute(self, *args, **kwargs):
            pass
        async def fetchone(self, *args, **kwargs):
            return None
    return ExecutionStateStore(MockDB())


@pytest.fixture
def executor(mock_mcp_manager, mock_secret_store, mock_state_store):
    """Create executor instance."""
    return WorkflowExecutor(
        mcp_manager=mock_mcp_manager,
        secret_store=mock_secret_store,
        state_store=mock_state_store,
    )


# =============================================================================
# Multi-Agent Node Tests
# =============================================================================

@pytest.mark.asyncio
async def test_execute_multi_agent_mock_mode(executor):
    """Test multi-agent node returns mock output in mock mode."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "TestTeam",
            "strategy": "coordinator",
            "members": [
                {"name": "agent1", "role": "worker"},
                {"name": "agent2", "role": "specialist"},
            ],
        },
    )
    context = {"input": "test task"}

    result = await executor._execute_node(node, context, mode="mock")

    assert isinstance(result, dict)
    assert "output" in result
    assert "[Mock]" in result["output"]
    assert "TestTeam" in result["output"]
    assert result["strategy"] == "coordinator"
    assert result["rounds"] == 1
    assert result["totalCost"] == 0.0
    assert result["totalTokens"] == 0
    assert result["agentOutputs"] == {}
    assert result["messageCount"] == 0


@pytest.mark.asyncio
async def test_execute_multi_agent_node_routing(executor):
    """Test that multi_agent type routes correctly in _execute_node."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={"name": "TestTeam", "members": []},
    )
    context = {"input": "test"}

    # In mock mode, should route to _get_mock_output
    result = await executor._execute_node(node, context, mode="mock")

    assert isinstance(result, dict)
    assert "output" in result
    assert result["strategy"] is not None


def test_mock_multi_agent_output_structure(executor):
    """Test that mock output has all expected fields."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "MyTeam",
            "strategy": "debate",
            "members": [{"name": "a1"}, {"name": "a2"}],
        },
    )

    output = executor._get_mock_output(node)

    # Verify all expected fields are present
    assert "output" in output
    assert "strategy" in output
    assert "rounds" in output
    assert "totalCost" in output
    assert "totalTokens" in output
    assert "agentOutputs" in output
    assert "messageCount" in output
    assert "agentEvents" in output

    # Verify types
    assert isinstance(output["output"], str)
    assert isinstance(output["strategy"], str)
    assert isinstance(output["rounds"], int)
    assert isinstance(output["totalCost"], float)
    assert isinstance(output["totalTokens"], int)
    assert isinstance(output["agentOutputs"], dict)
    assert isinstance(output["messageCount"], int)
    assert isinstance(output["agentEvents"], list)
    assert output["agentEvents"] == []


def test_mock_multi_agent_empty_members(executor):
    """Test mock output when no members are configured."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={"name": "EmptyTeam", "members": []},
    )

    output = executor._get_mock_output(node)

    # Should still return valid structure
    assert isinstance(output, dict)
    assert "output" in output
    assert "EmptyTeam" in output["output"]


def test_mock_multi_agent_minimal_data(executor):
    """Test mock output with minimal node data."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={},  # No name, no strategy, no members
    )

    output = executor._get_mock_output(node)

    # Should use defaults
    assert output["strategy"] == "coordinator"  # Default
    assert "team" in output["output"]  # Default team name


def test_mock_multi_agent_all_strategies(executor):
    """Test mock output for all supported strategies."""
    strategies = ["coordinator", "round_robin", "debate", "map_reduce"]

    for strategy in strategies:
        node = WorkflowNode(
            id=f"team_{strategy}",
            type="multi_agent",
            data={"name": "Team", "strategy": strategy},
        )

        output = executor._get_mock_output(node)
        assert output["strategy"] == strategy


@pytest.mark.asyncio
async def test_multi_agent_workflow_integration(executor):
    """Test multi-agent node in a complete workflow (mock mode)."""
    nodes = [
        WorkflowNode(id="start", type="agent", data={"name": "Input"}),
        WorkflowNode(
            id="team",
            type="multi_agent",
            data={
                "name": "ResearchTeam",
                "strategy": "coordinator",
                "members": [
                    {"name": "researcher", "role": "specialist"},
                    {"name": "writer", "role": "worker"},
                ],
            },
        ),
    ]
    edges = [
        WorkflowEdge(id="e1", source="start", target="team"),
    ]
    workflow = Workflow(id="w1", name="test_workflow", nodes=nodes, edges=edges)

    result = await executor.run(workflow, input="test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 2

    # Check team node execution
    team_execution = [ne for ne in result.node_executions if ne.node_id == "team"][0]
    assert team_execution.status == ExecutionStatus.COMPLETED
    assert isinstance(team_execution.output, dict)
    assert "output" in team_execution.output
    assert team_execution.output["strategy"] == "coordinator"


def test_mock_multi_agent_budget_exceeded_field(executor):
    """Test that mock output includes budgetExceeded field."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={"name": "Team", "strategy": "coordinator"},
    )

    output = executor._get_mock_output(node)
    assert "budgetExceeded" in output
    assert output["budgetExceeded"] is False


# =============================================================================
# _run_multi_agent Integration Tests (P2-2, P2-3, P2-4, P2-5)
# =============================================================================


def _make_mock_team_result(total_cost=0.05, total_tokens=500):
    """Create a mock TeamResult for testing."""
    from agentchord.orchestration.types import (
        AgentOutput,
        TeamResult,
        TeamRole,
    )

    return TeamResult(
        output="Team result output",
        agent_outputs={
            "agent1": AgentOutput(
                agent_name="agent1",
                role=TeamRole.WORKER,
                output="Agent 1 output",
                tokens=250,
                cost=0.025,
            ),
        },
        messages=[],
        total_cost=total_cost,
        total_tokens=total_tokens,
        rounds=2,
        duration_ms=100,
        strategy="coordinator",
        team_name="TestTeam",
    )


def _make_mock_settings():
    """Create a mock settings object."""
    settings = MagicMock()
    settings.default_llm_model = "gpt-4o"
    settings.openai_api_key = "sk-test"
    settings.openai_base_url = None
    settings.llm_timeout = 30
    return settings


@pytest.mark.asyncio
async def test_run_multi_agent_role_mapping(executor):
    """Member roles are mapped to TeamRole enum correctly."""
    from agentchord.orchestration.types import TeamRole

    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "RoleTeam",
            "strategy": "coordinator",
            "members": [
                {"name": "coord", "role": "coordinator"},
                {"name": "worker1", "role": "worker"},
                {"name": "reviewer1", "role": "reviewer"},
                {"name": "spec1", "role": "specialist"},
                {"name": "unknown_role", "role": "nonexistent"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        # Create a real team instance that we can inspect
        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            # Simulate AgentTeam behavior: create TeamMember for each Agent
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    # Verify roles were patched correctly
    member_roles = {tm.name: tm.role for tm in team_instance._members}
    assert member_roles["coord"] == TeamRole.COORDINATOR
    assert member_roles["worker1"] == TeamRole.WORKER
    assert member_roles["reviewer1"] == TeamRole.REVIEWER
    assert member_roles["spec1"] == TeamRole.SPECIALIST
    assert member_roles["unknown_role"] == TeamRole.WORKER  # fallback


@pytest.mark.asyncio
async def test_run_multi_agent_capabilities_passed(executor):
    """Member capabilities are preserved in TeamMember."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "CapTeam",
            "strategy": "coordinator",
            "members": [
                {"name": "searcher", "role": "specialist", "capabilities": ["search", "summarize"]},
                {"name": "plain", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    member_caps = {tm.name: tm.capabilities for tm in team_instance._members}
    assert member_caps["searcher"] == ["search", "summarize"]
    assert member_caps["plain"] == []


@pytest.mark.asyncio
async def test_run_multi_agent_coordinator_id(executor):
    """coordinatorId selects the coordinator agent passed to AgentTeam."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "CoordTeam",
            "strategy": "coordinator",
            "coordinatorId": "lead",
            "members": [
                {"name": "lead", "role": "coordinator"},
                {"name": "worker1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()
    captured_kwargs = {}

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            captured_kwargs.update(kwargs)
            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    # Verify coordinator was passed to AgentTeam
    assert captured_kwargs["coordinator"] is not None
    assert captured_kwargs["coordinator"].name == "lead"


@pytest.mark.asyncio
async def test_run_multi_agent_coordinator_id_none(executor):
    """No coordinatorId means coordinator=None passed to AgentTeam."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "NoCoordTeam",
            "strategy": "round_robin",
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()
    captured_kwargs = {}

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            captured_kwargs.update(kwargs)
            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    assert captured_kwargs["coordinator"] is None


@pytest.mark.asyncio
async def test_run_multi_agent_cost_budget_exceeded(executor):
    """budgetExceeded is True when cost exceeds costBudget."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "BudgetTeam",
            "strategy": "coordinator",
            "costBudget": 0.01,  # Very low budget
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    # total_cost=0.05 exceeds budget of 0.01
    mock_result = _make_mock_team_result(total_cost=0.05)

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    assert result["budgetExceeded"] is True
    assert result["totalCost"] == 0.05


@pytest.mark.asyncio
async def test_run_multi_agent_cost_budget_not_exceeded(executor):
    """budgetExceeded is False when cost is within budget."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "BudgetTeam",
            "strategy": "coordinator",
            "costBudget": 1.0,  # Generous budget
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result(total_cost=0.05)

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    assert result["budgetExceeded"] is False


@pytest.mark.asyncio
async def test_run_multi_agent_no_cost_budget(executor):
    """budgetExceeded is False when no costBudget is set."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "NoBudgetTeam",
            "strategy": "coordinator",
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result(total_cost=100.0)

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    # No budget set, so never exceeded
    assert result["budgetExceeded"] is False


# =============================================================================
# _MultiAgentEventCollector Unit Tests (P2-1)
# =============================================================================


@pytest.mark.asyncio
async def test_event_collector_emit_records_events():
    """_MultiAgentEventCollector.emit() accumulates events in order."""
    collector = _MultiAgentEventCollector()

    await collector.emit("orchestration_start", team="TestTeam", strategy="debate")
    await collector.emit("agent_delegated", agent_name="agent1", task="subtask")
    await collector.emit("agent_completed", agent_name="agent1", output="result")

    assert len(collector.events) == 3
    assert collector.events[0] == {
        "type": "orchestration_start",
        "team": "TestTeam",
        "strategy": "debate",
    }
    assert collector.events[1] == {
        "type": "agent_delegated",
        "agent_name": "agent1",
        "task": "subtask",
    }
    assert collector.events[2] == {
        "type": "agent_completed",
        "agent_name": "agent1",
        "output": "result",
    }


@pytest.mark.asyncio
async def test_event_collector_starts_empty():
    """_MultiAgentEventCollector starts with an empty events list."""
    collector = _MultiAgentEventCollector()
    assert collector.events == []


@pytest.mark.asyncio
async def test_event_collector_preserves_all_kwargs():
    """All keyword arguments are captured in the event dict."""
    collector = _MultiAgentEventCollector()

    await collector.emit(
        "map_phase_start",
        agent_count=3,
        custom_field="custom_value",
        nested={"key": "val"},
    )

    assert len(collector.events) == 1
    event = collector.events[0]
    assert event["type"] == "map_phase_start"
    assert event["agent_count"] == 3
    assert event["custom_field"] == "custom_value"
    assert event["nested"] == {"key": "val"}


# =============================================================================
# Event Collector Integration with _run_multi_agent (P2-1)
# =============================================================================


@pytest.mark.asyncio
async def test_run_multi_agent_passes_callbacks_to_team(executor):
    """_run_multi_agent passes _MultiAgentEventCollector as callbacks to AgentTeam."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "EventTeam",
            "strategy": "coordinator",
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()
    captured_kwargs = {}

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            captured_kwargs.update(kwargs)
            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        await executor._run_multi_agent(node, context)

    # Verify callbacks kwarg was passed and is a _MultiAgentEventCollector
    assert "callbacks" in captured_kwargs
    assert isinstance(captured_kwargs["callbacks"], _MultiAgentEventCollector)


@pytest.mark.asyncio
async def test_run_multi_agent_result_contains_agent_events(executor):
    """_run_multi_agent result includes agentEvents from the event collector."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "EventTeam",
            "strategy": "map_reduce",
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.close = AsyncMock()
        team_instance._members = []

        # Simulate AgentTeam.run() emitting events via the callbacks
        async def mock_run(task):
            # The callbacks object is the event collector passed to AgentTeam
            callbacks = captured_kwargs.get("callbacks")
            if callbacks:
                await callbacks.emit("orchestration_start", team="EventTeam")
                await callbacks.emit("agent_delegated", agent_name="agent1", task=task)
                await callbacks.emit("agent_completed", agent_name="agent1", output="done")
                await callbacks.emit("orchestration_end", team="EventTeam", rounds=2)
            return mock_result

        team_instance.run = mock_run

        captured_kwargs = {}

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            captured_kwargs.update(kwargs)
            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    # Verify agentEvents is present and contains the emitted events
    assert "agentEvents" in result
    assert isinstance(result["agentEvents"], list)
    assert len(result["agentEvents"]) == 4

    event_types = [e["type"] for e in result["agentEvents"]]
    assert event_types == [
        "orchestration_start",
        "agent_delegated",
        "agent_completed",
        "orchestration_end",
    ]

    # Verify event payloads
    assert result["agentEvents"][0]["team"] == "EventTeam"
    assert result["agentEvents"][1]["agent_name"] == "agent1"
    assert result["agentEvents"][2]["output"] == "done"
    assert result["agentEvents"][3]["rounds"] == 2


@pytest.mark.asyncio
async def test_run_multi_agent_empty_events_when_no_callbacks_fired(executor):
    """agentEvents is an empty list when no events are emitted."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "SilentTeam",
            "strategy": "coordinator",
            "members": [
                {"name": "agent1", "role": "worker"},
            ],
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        result = await executor._run_multi_agent(node, context)

    assert "agentEvents" in result
    assert result["agentEvents"] == []


@pytest.mark.asyncio
async def test_mock_mode_multi_agent_includes_agent_events(executor):
    """Mock mode multi-agent output includes agentEvents field."""
    node = WorkflowNode(
        id="team1",
        type="multi_agent",
        data={
            "name": "MockTeam",
            "strategy": "coordinator",
            "members": [{"name": "a1"}],
        },
    )
    context = {"input": "test"}

    result = await executor._execute_node(node, context, mode="mock")

    assert "agentEvents" in result
    assert isinstance(result["agentEvents"], list)
    assert result["agentEvents"] == []


@pytest.mark.asyncio
async def test_multi_agent_enable_consult_passed_to_team(executor):
    """enable_consult is passed to AgentTeam."""
    node = WorkflowNode(
        id="n1",
        type="multi_agent",
        data={
            "name": "test-team",
            "members": [
                {"name": "a1", "model": "gpt-4o-mini", "role": "worker", "systemPrompt": "", "capabilities": [], "temperature": 0.7},
            ],
            "strategy": "round_robin",
            "maxRounds": 3,
            "costBudget": 0,
            "enableConsult": True,
            "maxConsultDepth": 2,
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        captured_kwargs = {}

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            captured_kwargs.update(kwargs)
            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        await executor._run_multi_agent(node, context)

        call_kwargs = captured_kwargs
        assert call_kwargs["enable_consult"] is True
        assert call_kwargs["max_consult_depth"] == 2


@pytest.mark.asyncio
async def test_multi_agent_consult_defaults(executor):
    """enable_consult defaults to False when not specified."""
    node = WorkflowNode(
        id="n1",
        type="multi_agent",
        data={
            "name": "test-team",
            "members": [
                {"name": "a1", "model": "gpt-4o-mini", "role": "worker", "systemPrompt": "", "capabilities": [], "temperature": 0.7},
            ],
            "strategy": "round_robin",
            "maxRounds": 3,
            "costBudget": 0,
        },
    )
    context = {"input": "test input"}

    mock_result = _make_mock_team_result()

    with (
        patch("app.core.executor.WorkflowExecutor._create_llm_provider") as mock_provider,
        patch("app.core.executor.WorkflowExecutor._build_agent_tools", new_callable=AsyncMock, return_value=[]),
        patch("agentchord.AgentTeam") as MockTeam,
        patch("app.config.get_settings", return_value=_make_mock_settings()),
    ):
        mock_provider.return_value = MagicMock()

        team_instance = MagicMock()
        team_instance.run = AsyncMock(return_value=mock_result)
        team_instance.close = AsyncMock()
        team_instance._members = []

        captured_kwargs = {}

        def capture_team_init(**kwargs):
            from agentchord.orchestration.types import TeamMember, TeamRole as TR

            captured_kwargs.update(kwargs)
            members = kwargs.get("members", [])
            for m in members:
                tm = TeamMember(name=m.name, role=TR.WORKER)
                team_instance._members.append(tm)
            return team_instance

        MockTeam.side_effect = lambda **kwargs: capture_team_init(**kwargs)

        await executor._run_multi_agent(node, context)

        call_kwargs = captured_kwargs
        assert call_kwargs["enable_consult"] is False
        assert call_kwargs["max_consult_depth"] == 1
