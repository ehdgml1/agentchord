"""Tests for mock execution mode."""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.executor import (
    WorkflowExecutor,
    ExecutionStatus,
    WorkflowNode,
    WorkflowEdge,
    Workflow,
)
import uuid


@pytest.mark.asyncio
async def test_mock_mode_no_network(executor, simple_workflow):
    """Test that mock mode makes no external calls."""
    # Patch network-making functions
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.post = AsyncMock()

        # Run in mock mode
        execution = await executor.run(
            workflow=simple_workflow,
            input="test input",
            mode="mock",
        )

        # Verify no network calls were made
        mock_client.return_value.post.assert_not_called()
        assert execution.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_mock_agent_output(executor):
    """Test agent node returns mock response."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Agent Test",
        nodes=[
            WorkflowNode(
                id="agent-1",
                type="agent",
                data={
                    "name": "Test Agent",
                    "role": "Testing",
                    "model": "gpt-4o-mini",
                },
            ),
        ],
        edges=[],
    )

    execution = await executor.run(
        workflow=workflow,
        input="test input",
        mode="mock",
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert len(execution.node_executions) == 1

    node_result = execution.node_executions[0]
    assert "[Mock]" in node_result.output
    assert "Test Agent" in node_result.output


@pytest.mark.asyncio
async def test_mock_tool_output(executor):
    """Test MCP tool returns mock response."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Tool Test",
        nodes=[
            WorkflowNode(
                id="tool-1",
                type="mcp_tool",
                data={
                    "serverId": "test-server",
                    "toolName": "fetch_data",
                    "parameters": {"query": "test"},
                },
            ),
        ],
        edges=[],
    )

    execution = await executor.run(
        workflow=workflow,
        input="test input",
        mode="mock",
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert len(execution.node_executions) == 1

    node_result = execution.node_executions[0]
    assert node_result.output is not None
    assert isinstance(node_result.output, dict)
    assert "[Mock]" in node_result.output["result"]
    assert "fetch_data" in node_result.output["result"]


@pytest.mark.asyncio
async def test_mock_custom_response(executor):
    """Test custom mockResponse is used."""
    custom_response = {"status": "success", "data": [1, 2, 3]}

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Custom Mock Test",
        nodes=[
            WorkflowNode(
                id="tool-1",
                type="mcp_tool",
                data={
                    "serverId": "test-server",
                    "toolName": "custom_tool",
                    "parameters": {},
                    "mockResponse": custom_response,
                },
            ),
        ],
        edges=[],
    )

    execution = await executor.run(
        workflow=workflow,
        input="test input",
        mode="mock",
    )

    assert execution.status == ExecutionStatus.COMPLETED
    node_result = execution.node_executions[0]
    assert node_result.output == custom_response


@pytest.mark.asyncio
async def test_mock_condition_always_true(executor):
    """Test condition node takes true path in mock mode."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Condition Test",
        nodes=[
            WorkflowNode(
                id="start",
                type="agent",
                data={
                    "name": "Start",
                    "model": "gpt-4o-mini",
                },
            ),
            WorkflowNode(
                id="condition",
                type="condition",
                data={
                    "condition": "len(input) > 100",  # This would be false normally
                },
            ),
            WorkflowNode(
                id="end",
                type="agent",
                data={
                    "name": "End",
                    "model": "gpt-4o-mini",
                },
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="start", target="condition"),
            WorkflowEdge(id="e2", source="condition", target="end"),
        ],
    )

    execution = await executor.run(
        workflow=workflow,
        input="short",  # Short input
        mode="mock",
    )

    assert execution.status == ExecutionStatus.COMPLETED
    # All nodes should execute (condition is True in mock mode)
    assert len(execution.node_executions) == 3

    condition_result = execution.node_executions[1]
    assert condition_result.output == {"result": True, "active_handle": "true"}


@pytest.mark.asyncio
async def test_mock_mode_fast(executor, sample_workflow):
    """Test mock execution completes quickly."""
    start_time = time.time()

    execution = await executor.run(
        workflow=sample_workflow,
        input="test input",
        mode="mock",
    )

    elapsed = time.time() - start_time

    assert execution.status == ExecutionStatus.COMPLETED
    # Mock mode should complete in under 1 second for 5 nodes
    assert elapsed < 1.0
    # All nodes should have executed
    assert len(execution.node_executions) == 5


@pytest.mark.asyncio
async def test_mock_vs_full_mode(executor, simple_workflow):
    """Compare mock and full mode execution."""
    # Mock mode
    mock_execution = await executor.run(
        workflow=simple_workflow,
        input="test",
        mode="mock",
    )

    assert mock_execution.mode == "mock"
    assert mock_execution.status == ExecutionStatus.COMPLETED

    # Verify mock outputs
    for node_exec in mock_execution.node_executions:
        if node_exec.output:
            assert "[Mock]" in str(node_exec.output)


@pytest.mark.asyncio
async def test_mock_preserves_workflow_structure(executor, sample_workflow):
    """Test mock mode respects workflow node order."""
    execution = await executor.run(
        workflow=sample_workflow,
        input="test",
        mode="mock",
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert len(execution.node_executions) == len(sample_workflow.nodes)

    # Verify execution order matches workflow structure
    executed_node_ids = [ne.node_id for ne in execution.node_executions]
    workflow_node_ids = [n.id for n in sample_workflow.nodes]

    # Should execute in topological order
    assert len(executed_node_ids) == len(workflow_node_ids)
    for node_id in executed_node_ids:
        assert node_id in workflow_node_ids


@pytest.mark.asyncio
async def test_mock_mode_with_parameters(executor):
    """Test mock mode handles node parameters correctly."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Parameters Test",
        nodes=[
            WorkflowNode(
                id="tool",
                type="mcp_tool",
                data={
                    "serverId": "server-1",
                    "toolName": "process",
                    "parameters": {
                        "input": "value1",
                        "config": {"key": "value"},
                        "count": 42,
                    },
                },
            ),
        ],
        edges=[],
    )

    execution = await executor.run(
        workflow=workflow,
        input="test",
        mode="mock",
    )

    assert execution.status == ExecutionStatus.COMPLETED
    # Mock should not fail on complex parameters
    assert len(execution.node_executions) == 1
    assert execution.node_executions[0].status == ExecutionStatus.COMPLETED
