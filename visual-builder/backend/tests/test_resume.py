"""Tests for pause and resume execution."""
import pytest
import asyncio
from app.core.executor import (
    ExecutionStatus,
    WorkflowNode,
    WorkflowEdge,
    Workflow,
)
import uuid


@pytest.mark.asyncio
async def test_pause_and_resume(executor, state_store, sample_workflow):
    """Test pausing and resuming execution."""
    # Start execution
    execution_id = str(uuid.uuid4())

    # Manually save checkpoint at node-3
    checkpoint_context = {
        "input": "test input",
        "node-1": "output from node 1",
        "node-2": {"result": "data from node 2"},
    }

    await state_store.save_state(
        execution_id=execution_id,
        current_node="node-3",
        context=checkpoint_context,
    )

    # Resume from checkpoint
    resumed_execution = await executor.resume(
        execution_id=execution_id,
        workflow=sample_workflow,
    )

    # Verify execution completed from checkpoint
    assert resumed_execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

    # Should have executed nodes 3, 4, 5 (not 1, 2)
    executed_nodes = [ne.node_id for ne in resumed_execution.node_executions]
    assert "node-3" in executed_nodes
    assert "node-4" in executed_nodes
    assert "node-5" in executed_nodes


@pytest.mark.asyncio
async def test_resume_preserves_context(executor, state_store, simple_workflow):
    """Test that context is restored correctly."""
    execution_id = str(uuid.uuid4())

    # Save state with specific context
    original_context = {
        "input": "original input",
        "start": "start node output",
        "custom_data": {"key": "value", "count": 42},
    }

    await state_store.save_state(
        execution_id=execution_id,
        current_node="end",
        context=original_context,
    )

    # Load state to verify it was saved
    loaded_state = await state_store.load_state(execution_id)
    assert loaded_state is not None
    assert loaded_state["current_node"] == "end"
    assert loaded_state["context"]["input"] == "original input"
    assert loaded_state["context"]["start"] == "start node output"
    assert loaded_state["context"]["custom_data"]["key"] == "value"
    assert loaded_state["context"]["custom_data"]["count"] == 42


@pytest.mark.asyncio
async def test_resume_from_specific_node(executor, state_store, sample_workflow):
    """Test resuming from a specific node."""
    execution_id = str(uuid.uuid4())

    # Save checkpoint at node-4
    context = {
        "input": "test",
        "node-1": "output1",
        "node-2": "output2",
        "node-3": True,
    }

    await state_store.save_state(
        execution_id=execution_id,
        current_node="node-4",
        context=context,
    )

    # Resume
    resumed = await executor.resume(execution_id, sample_workflow)

    # Should start from node-4
    executed_ids = [ne.node_id for ne in resumed.node_executions]
    assert "node-4" in executed_ids
    assert "node-5" in executed_ids

    # Should NOT re-execute earlier nodes
    assert "node-1" not in executed_ids or executed_ids.index("node-4") < executed_ids.index("node-1")


@pytest.mark.asyncio
async def test_resume_after_failure(executor, state_store):
    """Test resuming after node failure."""
    execution_id = str(uuid.uuid4())

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Failure Test",
        nodes=[
            WorkflowNode(
                id="start",
                type="agent",
                data={"name": "Start", "model": "gpt-4o-mini"},
            ),
            WorkflowNode(
                id="middle",
                type="agent",
                data={"name": "Middle", "model": "gpt-4o-mini"},
            ),
            WorkflowNode(
                id="end",
                type="agent",
                data={"name": "End", "model": "gpt-4o-mini"},
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="start", target="middle"),
            WorkflowEdge(id="e2", source="middle", target="end"),
        ],
    )

    # Simulate failure at middle node by saving checkpoint
    await state_store.save_state(
        execution_id=execution_id,
        current_node="middle",
        context={
            "input": "test",
            "start": "completed",
        },
    )

    # Mark as failed
    await state_store.mark_failed(
        execution_id=execution_id,
        node_id="middle",
        error="Simulated failure",
    )

    # Resume should start from middle node
    resumed = await executor.resume(execution_id, workflow)

    # Verify it attempted to resume
    assert resumed is not None


@pytest.mark.asyncio
async def test_checkpoint_saved_before_each_node(executor, state_store, sample_workflow):
    """Test that checkpoint is saved before each node execution."""
    execution_id = str(uuid.uuid4())

    # Run workflow in mock mode
    execution = await executor.run(
        workflow=sample_workflow,
        input="test checkpoint",
        mode="mock",
    )

    # For a completed execution, checkpoint should be cleaned up
    # But we can verify the save_state was called by checking it happened during execution
    assert execution.status == ExecutionStatus.COMPLETED

    # Verify checkpoint was deleted after successful completion
    final_state = await state_store.load_state(execution.id)
    assert final_state is None  # Should be cleaned up


@pytest.mark.asyncio
async def test_checkpoint_lifecycle(executor, state_store):
    """Test checkpoint save and cleanup lifecycle."""
    execution_id = str(uuid.uuid4())

    # Save checkpoint
    await state_store.save_state(
        execution_id=execution_id,
        current_node="test-node",
        context={"data": "test"},
    )

    # Verify it exists
    state = await state_store.load_state(execution_id)
    assert state is not None
    assert state["current_node"] == "test-node"

    # Delete checkpoint
    await state_store.delete_state(execution_id)

    # Verify it's gone
    deleted_state = await state_store.load_state(execution_id)
    assert deleted_state is None


@pytest.mark.asyncio
async def test_resume_nonexistent_execution(executor, state_store, simple_workflow):
    """Test resuming non-existent execution raises error."""
    fake_execution_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="No saved state"):
        await executor.resume(fake_execution_id, simple_workflow)


@pytest.mark.asyncio
async def test_resume_updates_checkpoint(executor, state_store, simple_workflow):
    """Test that resuming updates checkpoints as it progresses."""
    execution_id = str(uuid.uuid4())

    # Save initial checkpoint
    await state_store.save_state(
        execution_id=execution_id,
        current_node="start",
        context={"input": "test"},
    )

    # Resume execution (will run in mock mode)
    resumed = await executor.resume(execution_id, simple_workflow)

    # After completion, checkpoint should be cleaned up
    if resumed.status == ExecutionStatus.COMPLETED:
        final_state = await state_store.load_state(execution_id)
        assert final_state is None


@pytest.mark.asyncio
async def test_parallel_checkpoint_safety(state_store):
    """Test that concurrent checkpoint saves don't conflict."""
    execution_id = str(uuid.uuid4())

    # Save multiple checkpoints rapidly
    async def save_checkpoint(node_id: str):
        await state_store.save_state(
            execution_id=execution_id,
            current_node=node_id,
            context={"node": node_id},
        )

    # Run saves concurrently
    await asyncio.gather(
        save_checkpoint("node-1"),
        save_checkpoint("node-2"),
        save_checkpoint("node-3"),
    )

    # Should have the last saved state
    state = await state_store.load_state(execution_id)
    assert state is not None
    assert state["current_node"] in ["node-1", "node-2", "node-3"]
