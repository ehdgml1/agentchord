"""Test WorkflowExecutor with multiple nodes of each type.

Verifies that the executor correctly handles workflows with:
- Multiple sequential agents
- Multiple parallel agents
- Multiple MCP tools
- Multiple conditions
- Mixed complex workflows
- All node types present
- Diamond patterns
- Stress tests with many duplicate types
"""
import pytest
import uuid
from datetime import datetime, UTC

from app.core.executor import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    ExecutionStatus,
)


@pytest.mark.asyncio
async def test_multiple_agents_chain(executor):
    """Test 3 sequential agents: agent1 → agent2 → agent3."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={
                "name": "Agent 1",
                "role": "First processor",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
            },
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={
                "name": "Agent 2",
                "role": "Second processor",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
            },
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={
                "name": "Agent 3",
                "role": "Final processor",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="agent2"),
        WorkflowEdge(id="e2", source="agent2", target="agent3"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="3 Agent Chain",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 3
    assert result.error is None

    # Verify all 3 agents executed
    executed_ids = {ne.node_id for ne in result.node_executions}
    assert executed_ids == {"agent1", "agent2", "agent3"}

    # Verify all completed successfully
    for ne in result.node_executions:
        assert ne.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_multiple_agents_parallel(executor):
    """Test fan-out: agent1 → agent2, agent1 → agent3 (parallel)."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={
                "name": "Agent 1",
                "role": "Input processor",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={
                "name": "Agent 2",
                "role": "Branch A",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={
                "name": "Agent 3",
                "role": "Branch B",
                "model": "gpt-4o-mini",
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="agent2"),
        WorkflowEdge(id="e2", source="agent1", target="agent3"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Parallel Agents",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    # agent1 executes, then agent2 and agent3 can execute in parallel
    assert len(result.node_executions) == 3
    assert result.error is None

    executed_ids = {ne.node_id for ne in result.node_executions}
    assert executed_ids == {"agent1", "agent2", "agent3"}


@pytest.mark.asyncio
async def test_multiple_mcp_tools(executor):
    """Test agent1 → mcp1, agent1 → mcp2 (two MCP tools in parallel)."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={
                "name": "Data Generator",
                "role": "Generate data",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="mcp1",
            type="mcp_tool",
            data={
                "serverId": "server-a",
                "toolName": "tool_alpha",
                "parameters": {"input": "data"},
            },
        ),
        WorkflowNode(
            id="mcp2",
            type="mcp_tool",
            data={
                "serverId": "server-b",
                "toolName": "tool_beta",
                "parameters": {"input": "data"},
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="mcp1"),
        WorkflowEdge(id="e2", source="agent1", target="mcp2"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Parallel MCP Tools",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 3
    assert result.error is None

    executed_ids = {ne.node_id for ne in result.node_executions}
    assert executed_ids == {"agent1", "mcp1", "mcp2"}


@pytest.mark.asyncio
async def test_multiple_conditions(executor):
    """Test agent1 → condition1 → agent2, condition1 → agent3 (branching)."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={
                "name": "Checker",
                "role": "Check input",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="condition1",
            type="condition",
            data={
                "condition": "len(str(input)) > 5",
            },
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={
                "name": "True Branch",
                "role": "Process if true",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={
                "name": "False Branch",
                "role": "Process if false",
                "model": "gpt-4o-mini",
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="condition1"),
        WorkflowEdge(id="e2", source="condition1", target="agent2", source_handle="true"),
        WorkflowEdge(id="e3", source="condition1", target="agent3", source_handle="false"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Conditional Branching",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    # agent1, condition1, and ONE of agent2/agent3 should execute
    assert len(result.node_executions) == 3
    assert result.error is None

    executed_ids = {ne.node_id for ne in result.node_executions}
    assert "agent1" in executed_ids
    assert "condition1" in executed_ids
    # Exactly one of the branches should execute
    assert ("agent2" in executed_ids) or ("agent3" in executed_ids)


@pytest.mark.asyncio
async def test_mixed_complex_workflow(executor):
    """Test trigger → agent1 → parallel1 → agent2 → condition1 → agent3."""
    nodes = [
        WorkflowNode(
            id="trigger1",
            type="trigger",
            data={
                "triggerType": "manual",
            },
        ),
        WorkflowNode(
            id="agent1",
            type="agent",
            data={
                "name": "First Agent",
                "role": "Process",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="parallel1",
            type="parallel",
            data={
                "branches": 2,
            },
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={
                "name": "Second Agent",
                "role": "Process",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="condition1",
            type="condition",
            data={
                "condition": "true",
            },
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={
                "name": "Final Agent",
                "role": "Finalize",
                "model": "gpt-4o-mini",
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="trigger1", target="agent1"),
        WorkflowEdge(id="e2", source="agent1", target="parallel1"),
        WorkflowEdge(id="e3", source="parallel1", target="agent2"),
        WorkflowEdge(id="e4", source="agent2", target="condition1"),
        WorkflowEdge(id="e5", source="condition1", target="agent3", source_handle="true"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Mixed Complex",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    # All nodes should execute (trigger doesn't get executed as a node, it's a type marker)
    # In mock mode, we expect: trigger1, agent1, parallel1, agent2, condition1, agent3
    assert len(result.node_executions) >= 5
    assert result.error is None


@pytest.mark.asyncio
async def test_all_node_types_present(executor):
    """Test one of each type: trigger, agent, mcp_tool, condition, parallel, feedback_loop, rag, multi_agent."""
    nodes = [
        WorkflowNode(
            id="trigger1",
            type="trigger",
            data={"triggerType": "manual"},
        ),
        WorkflowNode(
            id="agent1",
            type="agent",
            data={"name": "Agent", "role": "AI", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="mcp1",
            type="mcp_tool",
            data={"serverId": "srv", "toolName": "tool", "parameters": {}},
        ),
        WorkflowNode(
            id="condition1",
            type="condition",
            data={"condition": "true"},
        ),
        WorkflowNode(
            id="parallel1",
            type="parallel",
            data={"branches": 1},
        ),
        WorkflowNode(
            id="feedback1",
            type="feedback_loop",
            data={"maxIterations": 1, "stopCondition": "true"},
        ),
        WorkflowNode(
            id="rag1",
            type="rag",
            data={
                "documents": ["test doc"],
                "searchLimit": 3,
                "chunkSize": 200,
            },
        ),
        WorkflowNode(
            id="multi1",
            type="multi_agent",
            data={
                "name": "team",
                "members": [
                    {"name": "a1", "role": "worker", "model": "gpt-4o-mini"}
                ],
                "strategy": "coordinator",
            },
        ),
    ]

    # Chain them all together
    edges = [
        WorkflowEdge(id="e1", source="trigger1", target="agent1"),
        WorkflowEdge(id="e2", source="agent1", target="mcp1"),
        WorkflowEdge(id="e3", source="mcp1", target="condition1"),
        WorkflowEdge(id="e4", source="condition1", target="parallel1", source_handle="true"),
        WorkflowEdge(id="e5", source="parallel1", target="feedback1"),
        WorkflowEdge(id="e6", source="feedback1", target="rag1"),
        WorkflowEdge(id="e7", source="rag1", target="multi1"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="All Node Types",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    # All 8 node types should be present in executions
    # Note: feedback_loop may execute multiple times due to loop mechanism
    assert len(result.node_executions) >= 8
    assert result.error is None

    # Verify all 8 unique node IDs were executed at least once
    executed_types = {ne.node_id for ne in result.node_executions}
    assert executed_types == {
        "trigger1", "agent1", "mcp1", "condition1",
        "parallel1", "feedback1", "rag1", "multi1"
    }


@pytest.mark.asyncio
async def test_diamond_pattern(executor):
    """Test diamond: agent1 → agent2, agent1 → agent3, agent2 → agent4, agent3 → agent4."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={"name": "Start", "role": "Start", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={"name": "Left", "role": "Left path", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={"name": "Right", "role": "Right path", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="agent4",
            type="agent",
            data={"name": "Merge", "role": "Merge point", "model": "gpt-4o-mini"},
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="agent2"),
        WorkflowEdge(id="e2", source="agent1", target="agent3"),
        WorkflowEdge(id="e3", source="agent2", target="agent4"),
        WorkflowEdge(id="e4", source="agent3", target="agent4"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Diamond Pattern",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 4
    assert result.error is None

    executed_ids = {ne.node_id for ne in result.node_executions}
    assert executed_ids == {"agent1", "agent2", "agent3", "agent4"}


@pytest.mark.asyncio
async def test_duplicate_type_stress_test(executor):
    """Test 5 agent nodes in sequence (stress test)."""
    nodes = []
    edges = []

    for i in range(1, 6):
        nodes.append(
            WorkflowNode(
                id=f"agent{i}",
                type="agent",
                data={
                    "name": f"Agent {i}",
                    "role": f"Step {i}",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                },
            )
        )

        if i > 1:
            edges.append(
                WorkflowEdge(
                    id=f"e{i-1}",
                    source=f"agent{i-1}",
                    target=f"agent{i}",
                )
            )

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="5 Agent Sequence",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 5
    assert result.error is None

    # Verify all 5 agents executed
    executed_ids = {ne.node_id for ne in result.node_executions}
    assert executed_ids == {"agent1", "agent2", "agent3", "agent4", "agent5"}

    # Verify all completed successfully
    for ne in result.node_executions:
        assert ne.status == ExecutionStatus.COMPLETED
        assert ne.error is None


@pytest.mark.asyncio
async def test_multiple_conditions_complex(executor):
    """Test multiple conditions with different branch paths."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={"name": "Input", "role": "Process", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="cond1",
            type="condition",
            data={"condition": "len(str(input)) > 3"},
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={"name": "Long Path", "role": "Process", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={"name": "Short Path", "role": "Process", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="cond2",
            type="condition",
            data={"condition": "true"},
        ),
        WorkflowNode(
            id="agent4",
            type="agent",
            data={"name": "Final", "role": "Finish", "model": "gpt-4o-mini"},
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="cond1"),
        WorkflowEdge(id="e2", source="cond1", target="agent2", source_handle="true"),
        WorkflowEdge(id="e3", source="cond1", target="agent3", source_handle="false"),
        WorkflowEdge(id="e4", source="agent2", target="cond2"),
        WorkflowEdge(id="e5", source="agent3", target="cond2"),
        WorkflowEdge(id="e6", source="cond2", target="agent4", source_handle="true"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Multiple Conditions Complex",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    # Should have: agent1, cond1, one of (agent2, agent3), cond2, agent4
    assert len(result.node_executions) == 5
    assert result.error is None

    executed_ids = {ne.node_id for ne in result.node_executions}
    assert "agent1" in executed_ids
    assert "cond1" in executed_ids
    assert "cond2" in executed_ids
    assert "agent4" in executed_ids
    # Exactly one of the branches
    assert ("agent2" in executed_ids) or ("agent3" in executed_ids)


@pytest.mark.asyncio
async def test_context_propagation_multi_node(executor):
    """Test that context propagates correctly through multiple nodes."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={
                "name": "First",
                "role": "Generate data",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="agent2",
            type="agent",
            data={
                "name": "Second",
                "role": "Use previous output",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="agent3",
            type="agent",
            data={
                "name": "Third",
                "role": "Final processing",
                "model": "gpt-4o-mini",
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="agent2"),
        WorkflowEdge(id="e2", source="agent2", target="agent3"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Context Propagation Test",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "initial input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_executions) == 3

    # Verify context contains outputs from all nodes
    assert "agent1" in result.context
    assert "agent2" in result.context
    assert "agent3" in result.context

    # Verify final output is from the last node
    assert result.output is not None


@pytest.mark.asyncio
async def test_parallel_with_multiple_branches(executor):
    """Test parallel node with multiple downstream branches."""
    nodes = [
        WorkflowNode(
            id="agent1",
            type="agent",
            data={"name": "Start", "role": "Start", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="parallel1",
            type="parallel",
            data={"branches": 3},
        ),
        WorkflowNode(
            id="branch1",
            type="agent",
            data={"name": "Branch 1", "role": "Process", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="branch2",
            type="agent",
            data={"name": "Branch 2", "role": "Process", "model": "gpt-4o-mini"},
        ),
        WorkflowNode(
            id="branch3",
            type="agent",
            data={"name": "Branch 3", "role": "Process", "model": "gpt-4o-mini"},
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="agent1", target="parallel1"),
        WorkflowEdge(id="e2", source="parallel1", target="branch1"),
        WorkflowEdge(id="e3", source="parallel1", target="branch2"),
        WorkflowEdge(id="e4", source="parallel1", target="branch3"),
    ]

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Parallel Multiple Branches",
        nodes=nodes,
        edges=edges,
    )

    result = await executor.run(workflow, "test input", mode="mock")

    assert result.status == ExecutionStatus.COMPLETED
    # agent1, parallel1, branch1, branch2, branch3
    assert len(result.node_executions) == 5
    assert result.error is None

    executed_ids = {ne.node_id for ne in result.node_executions}
    assert executed_ids == {"agent1", "parallel1", "branch1", "branch2", "branch3"}
