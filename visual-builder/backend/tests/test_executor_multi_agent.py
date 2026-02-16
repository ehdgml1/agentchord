"""Tests for multi-agent execution handler.

Tests cover:
- Multi-agent node routing in _execute_node
- Mock mode output structure
- Empty members edge case
- Node type routing validation
"""

from __future__ import annotations

import pytest

from app.core.executor import (
    WorkflowExecutor,
    WorkflowNode,
    WorkflowEdge,
    Workflow,
    ExecutionStatus,
    ExecutionStateStore,
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

    # Verify types
    assert isinstance(output["output"], str)
    assert isinstance(output["strategy"], str)
    assert isinstance(output["rounds"], int)
    assert isinstance(output["totalCost"], float)
    assert isinstance(output["totalTokens"], int)
    assert isinstance(output["agentOutputs"], dict)
    assert isinstance(output["messageCount"], int)


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
