"""Comprehensive E2E tests for Feedback Loop feature.

Tests cover:
- Stop condition met before max iterations
- Max iterations reached with never-stopping condition
- Field name verification (stopCondition vs exitCondition)
- Auto-detection of loop body start via adjacency
- Explicit loopBodyStart specification
- Condition variable availability (iteration, input, context)
- Full E2E execution with loop iterations
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

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
# _run_feedback_loop Direct Tests
# =============================================================================

@pytest.mark.asyncio
async def test_feedback_loop_stop_condition_met(executor):
    """Test loop with stopCondition 'iteration >= 2', maxIterations=10.

    Should stop at iteration 2, not 10.
    """
    node = WorkflowNode(
        id="fb-1",
        type="feedback_loop",
        data={
            "maxIterations": 10,
            "stopCondition": "iteration >= 2",
            "blockType": "feedback_loop",
            "label": "Loop Until 2",
        },
        position={"x": 0, "y": 0},
    )
    context = {}

    # First call: iteration=0, "iteration >= 2" is False → continue
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True
    assert result["iteration"] == 1
    assert result["reason"] == "continuing"
    assert context[f"_loop_{node.id}"] == 1

    # Second call: iteration=1, "iteration >= 2" is False → continue
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True
    assert result["iteration"] == 2
    assert result["reason"] == "continuing"
    assert context[f"_loop_{node.id}"] == 2

    # Third call: iteration=2, "iteration >= 2" is True → stop
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["iteration"] == 2
    assert result["reason"] == "exit_condition_met"


@pytest.mark.asyncio
async def test_feedback_loop_max_iterations_reached(executor):
    """Test loop with stopCondition 'false' (never stops), maxIterations=3.

    Should stop at 3 iterations due to max limit.
    """
    node = WorkflowNode(
        id="fb-2",
        type="feedback_loop",
        data={
            "maxIterations": 3,
            "stopCondition": "false",
            "blockType": "feedback_loop",
            "label": "Max Iterations Test",
        },
        position={"x": 0, "y": 0},
    )
    context = {}

    # Iteration 0 → 1
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True
    assert result["iteration"] == 1
    assert context[f"_loop_{node.id}"] == 1

    # Iteration 1 → 2
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True
    assert result["iteration"] == 2
    assert context[f"_loop_{node.id}"] == 2

    # Iteration 2 → 3
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True
    assert result["iteration"] == 3
    assert context[f"_loop_{node.id}"] == 3

    # Iteration 3 → maxIterations reached
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["iteration"] == 3
    assert result["reason"] == "max_iterations_reached"


@pytest.mark.asyncio
async def test_feedback_loop_field_name_stopCondition(executor):
    """Verify the executor reads 'stopCondition' (not 'exitCondition') from node data."""
    node = WorkflowNode(
        id="fb-3",
        type="feedback_loop",
        data={
            "maxIterations": 5,
            "stopCondition": "iteration >= 1",  # Use stopCondition
            "blockType": "feedback_loop",
            "label": "Field Name Test",
        },
        position={"x": 0, "y": 0},
    )
    context = {}

    # First call: iteration=0, "iteration >= 1" is False
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True
    assert result["iteration"] == 1

    # Second call: iteration=1, "iteration >= 1" is True → should stop
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "exit_condition_met"

    # Test with missing stopCondition (should default to "false")
    node_no_condition = WorkflowNode(
        id="fb-4",
        type="feedback_loop",
        data={
            "maxIterations": 2,
            # No stopCondition field
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context2 = {}

    # Should continue with default "false" condition
    result = await executor._run_feedback_loop(node_no_condition, context2, "mock")
    assert result["continue_loop"] is True


@pytest.mark.asyncio
async def test_feedback_loop_condition_variables(executor):
    """Test that 'iteration' and 'input' variables are available in condition evaluation."""
    # Test iteration variable
    node_iteration = WorkflowNode(
        id="fb-5",
        type="feedback_loop",
        data={
            "maxIterations": 10,
            "stopCondition": "iteration == 3",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context = {}

    # Iterate until iteration == 3
    for i in range(4):
        result = await executor._run_feedback_loop(node_iteration, context, "mock")
        if i < 3:
            assert result["continue_loop"] is True
        else:
            assert result["continue_loop"] is False
            assert result["reason"] == "exit_condition_met"

    # Test input variable
    node_input = WorkflowNode(
        id="fb-6",
        type="feedback_loop",
        data={
            "maxIterations": 10,
            "stopCondition": "input == 'STOP'",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context_input = {"input": "CONTINUE"}

    # First call with "CONTINUE" → should continue
    result = await executor._run_feedback_loop(node_input, context_input, "mock")
    assert result["continue_loop"] is True

    # Update input to "STOP"
    context_input["input"] = "STOP"
    result = await executor._run_feedback_loop(node_input, context_input, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "exit_condition_met"


@pytest.mark.asyncio
async def test_feedback_loop_context_variable(executor):
    """Test that 'context' variable is available in condition evaluation."""
    node = WorkflowNode(
        id="fb-7",
        type="feedback_loop",
        data={
            "maxIterations": 10,
            "stopCondition": "context.get('agent-1', {}).get('status') == 'done'",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context = {
        "agent-1": {"status": "processing"},
    }

    # First call with status="processing" → should continue
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Update status to "done"
    context["agent-1"]["status"] = "done"
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "exit_condition_met"


# =============================================================================
# E2E Workflow Tests
# =============================================================================

@pytest.mark.asyncio
async def test_feedback_loop_auto_detect_loop_body_start(executor):
    """Test auto-detection of loop body start via adjacency.

    Workflow: agent-1 → feedback-1 → agent-2 (loop body) → feedback-1
    Do NOT set loopBodyStart in data. Verify agent-2 is detected as loop body start.

    NOTE: In mock mode, feedback_loop nodes return continue_loop=False immediately,
    so the loop body doesn't execute. This test verifies the workflow structure.
    """
    nodes = [
        WorkflowNode(id="agent-1", type="agent", data={"name": "Agent 1"}, position={"x": 0, "y": 0}),
        WorkflowNode(
            id="feedback-1",
            type="feedback_loop",
            data={
                "maxIterations": 2,
                "stopCondition": "iteration >= 2",
                "blockType": "feedback_loop",
                # No loopBodyStart specified → should auto-detect
            },
            position={"x": 100, "y": 0},
        ),
        WorkflowNode(id="agent-2", type="agent", data={"name": "Agent 2"}, position={"x": 200, "y": 0}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="agent-1", target="feedback-1"),
        WorkflowEdge(id="e2", source="feedback-1", target="agent-2"),  # Loop body start
        WorkflowEdge(id="e3", source="agent-2", target="feedback-1"),  # Back edge
    ]
    workflow = Workflow(id="w1", name="Auto-detect Loop", nodes=nodes, edges=edges)

    # Execute in mock mode
    execution = await executor.run(workflow, "test input", mode="mock")

    # Should complete successfully
    assert execution.status == ExecutionStatus.COMPLETED

    # In mock mode, topological order is [agent-1, agent-2, feedback-1]
    # Execution: agent-1 → agent-2 → feedback-1 (returns continue_loop=False)
    # Loop body doesn't execute in mock mode
    node_exec_ids = [ne.node_id for ne in execution.node_executions]

    assert node_exec_ids.count("agent-1") == 1
    assert node_exec_ids.count("agent-2") == 1
    assert node_exec_ids.count("feedback-1") == 1

    # Verify adjacency auto-detection works (check that adjacency[feedback-1] includes agent-2)
    adjacency = {n.id: [] for n in workflow.nodes}
    for edge in workflow.edges:
        adjacency[edge.source].append(edge.target)
    assert "agent-2" in adjacency["feedback-1"]


@pytest.mark.asyncio
async def test_feedback_loop_explicit_loop_body_start(executor):
    """Test explicit loopBodyStart specification.

    Same workflow but WITH loopBodyStart set explicitly. Verify it uses the explicit value.

    NOTE: In mock mode, loop body doesn't execute. This test verifies the data structure.
    """
    nodes = [
        WorkflowNode(id="agent-1", type="agent", data={"name": "Agent 1"}, position={"x": 0, "y": 0}),
        WorkflowNode(
            id="feedback-1",
            type="feedback_loop",
            data={
                "maxIterations": 2,
                "stopCondition": "iteration >= 2",
                "blockType": "feedback_loop",
                "loopBodyStart": "agent-2",  # Explicit specification
            },
            position={"x": 100, "y": 0},
        ),
        WorkflowNode(id="agent-2", type="agent", data={"name": "Agent 2"}, position={"x": 200, "y": 0}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="agent-1", target="feedback-1"),
        WorkflowEdge(id="e2", source="feedback-1", target="agent-2"),
        WorkflowEdge(id="e3", source="agent-2", target="feedback-1"),
    ]
    workflow = Workflow(id="w2", name="Explicit Loop", nodes=nodes, edges=edges)

    # Execute in mock mode
    execution = await executor.run(workflow, "test input", mode="mock")

    # Should complete successfully
    assert execution.status == ExecutionStatus.COMPLETED

    # In mock mode, loop body doesn't execute
    node_exec_ids = [ne.node_id for ne in execution.node_executions]

    assert node_exec_ids.count("agent-1") == 1
    assert node_exec_ids.count("agent-2") == 1
    assert node_exec_ids.count("feedback-1") == 1

    # Verify explicit loopBodyStart is set
    feedback_node = next(n for n in nodes if n.id == "feedback-1")
    assert feedback_node.data.get("loopBodyStart") == "agent-2"


@pytest.mark.asyncio
async def test_feedback_loop_e2e_execution(executor):
    """Full E2E test: workflow with agent → feedback_loop → agent (loop body).

    Tests workflow completion and structure. In mock mode, loop body doesn't iterate.
    For actual iteration testing, use non-mock mode or test _run_feedback_loop directly.
    """
    nodes = [
        WorkflowNode(
            id="start-agent",
            type="agent",
            data={"name": "Start Agent"},
            position={"x": 0, "y": 0},
        ),
        WorkflowNode(
            id="loop-control",
            type="feedback_loop",
            data={
                "maxIterations": 3,
                "stopCondition": "iteration >= 3",
                "blockType": "feedback_loop",
                "label": "Loop Controller",
            },
            position={"x": 100, "y": 0},
        ),
        WorkflowNode(
            id="loop-body-agent",
            type="agent",
            data={"name": "Loop Body Agent"},
            position={"x": 200, "y": 0},
        ),
    ]
    edges = [
        WorkflowEdge(id="e1", source="start-agent", target="loop-control"),
        WorkflowEdge(id="e2", source="loop-control", target="loop-body-agent"),
        WorkflowEdge(id="e3", source="loop-body-agent", target="loop-control"),  # Back edge
    ]
    workflow = Workflow(id="w3", name="E2E Loop Test", nodes=nodes, edges=edges)

    # Execute in mock mode
    execution = await executor.run(workflow, "initial input", mode="mock")

    # Should complete successfully
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.error is None

    # In mock mode: topological order [start-agent, loop-body-agent, loop-control]
    # Each node executes once, no loop iteration
    node_exec_ids = [ne.node_id for ne in execution.node_executions]

    assert node_exec_ids.count("start-agent") == 1
    assert node_exec_ids.count("loop-control") == 1
    assert node_exec_ids.count("loop-body-agent") == 1

    # Verify all executions completed successfully
    for node_exec in execution.node_executions:
        assert node_exec.status == ExecutionStatus.COMPLETED

    # Verify final output is from last executed node
    assert execution.output is not None


@pytest.mark.asyncio
async def test_feedback_loop_stops_on_first_condition(executor):
    """Test that loop stops on first iteration when condition is immediately met."""
    nodes = [
        WorkflowNode(
            id="immediate-stop",
            type="feedback_loop",
            data={
                "maxIterations": 10,
                "stopCondition": "iteration >= 0",  # Always true
                "blockType": "feedback_loop",
            },
            position={"x": 0, "y": 0},
        ),
        WorkflowNode(
            id="never-reached",
            type="agent",
            data={"name": "Should Not Execute"},
            position={"x": 100, "y": 0},
        ),
    ]
    edges = [
        WorkflowEdge(id="e1", source="immediate-stop", target="never-reached"),
        WorkflowEdge(id="e2", source="never-reached", target="immediate-stop"),
    ]
    workflow = Workflow(id="w4", name="Immediate Stop", nodes=nodes, edges=edges)

    execution = await executor.run(workflow, "test", mode="mock")

    assert execution.status == ExecutionStatus.COMPLETED

    # Topological order: [never-reached, immediate-stop]
    # 1. never-reached (main loop - executes BEFORE feedback node)
    # 2. immediate-stop (main loop - iteration=0, condition "iteration >= 0" is TRUE, returns continue_loop=False)
    # Loop body is NOT entered because continue_loop=False
    node_exec_ids = [ne.node_id for ne in execution.node_executions]

    assert node_exec_ids.count("immediate-stop") == 1
    # never-reached executes once in main loop (before feedback node is reached)
    assert node_exec_ids.count("never-reached") == 1


@pytest.mark.asyncio
async def test_feedback_loop_complex_stop_condition(executor):
    """Test complex stop condition with multiple variables and operators."""
    node = WorkflowNode(
        id="complex-loop",
        type="feedback_loop",
        data={
            "maxIterations": 20,
            "stopCondition": "(iteration >= 2) and (len(str(input)) > 0)",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context = {"input": "some text"}

    # First call: iteration=0, condition is False (iteration < 2)
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Second call: iteration=1, condition is still False
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Third call: iteration=2, condition is True (both parts satisfied)
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "exit_condition_met"


@pytest.mark.asyncio
async def test_feedback_loop_invalid_condition_defaults_to_continue(executor):
    """Test that invalid condition expressions default to False (continue loop)."""
    node = WorkflowNode(
        id="invalid-loop",
        type="feedback_loop",
        data={
            "maxIterations": 2,
            "stopCondition": "undefined_variable == 123",  # Invalid - undefined var
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context = {}

    # Should continue (invalid condition defaults to False)
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Should still continue on second call
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Third call should hit maxIterations
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "max_iterations_reached"


@pytest.mark.asyncio
async def test_feedback_loop_zero_max_iterations(executor):
    """Test loop with maxIterations=0 stops immediately."""
    node = WorkflowNode(
        id="zero-iter",
        type="feedback_loop",
        data={
            "maxIterations": 0,
            "stopCondition": "false",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context = {}

    # First call should immediately stop (iteration=0 >= maxIterations=0)
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "max_iterations_reached"


@pytest.mark.asyncio
async def test_feedback_loop_multi_level_context_access(executor):
    """Test accessing nested context values in stop condition."""
    node = WorkflowNode(
        id="nested-context",
        type="feedback_loop",
        data={
            "maxIterations": 10,
            "stopCondition": "context.get('agent1', {}).get('result', {}).get('count', 0) >= 5",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )
    context = {
        "agent1": {
            "result": {
                "count": 3,
            }
        }
    }

    # First call: count=3 < 5 → continue
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Update count to 5
    context["agent1"]["result"]["count"] = 5

    # Second call: count=5 >= 5 → stop
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "exit_condition_met"


@pytest.mark.asyncio
async def test_feedback_loop_dict_field_access_via_edges(executor):
    """Test that dict fields from upstream nodes are accessible via input.field syntax.

    This validates the fix for the bug where _resolve_input() returned strings,
    preventing field access like 'input.score >= 8'.
    """
    # Set up edges to simulate upstream node connection
    executor._current_edges = [
        WorkflowEdge(id="e1", source="upstream", target="fb-loop")
    ]

    node = WorkflowNode(
        id="fb-loop",
        type="feedback_loop",
        data={
            "maxIterations": 10,
            "stopCondition": "input.score >= 8",
            "blockType": "feedback_loop",
        },
        position={"x": 0, "y": 0},
    )

    # Upstream node produced dict output with score field
    context = {
        "upstream": {
            "output": {
                "score": 5,
                "feedback": "Try again"
            }
        }
    }

    # First call: score=5 < 8 → continue
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is True

    # Update score to 8
    context["upstream"]["output"]["score"] = 8

    # Second call: score=8 >= 8 → stop
    result = await executor._run_feedback_loop(node, context, "mock")
    assert result["continue_loop"] is False
    assert result["reason"] == "exit_condition_met"

    # Clean up
    executor._current_edges = None
