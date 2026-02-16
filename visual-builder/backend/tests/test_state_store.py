"""Tests for ExecutionStateStore functionality.

Tests save_state, load_state, mark_failed, and delete_state operations
using in-memory SQLite database.
"""
import pytest
import pytest_asyncio
import json
import uuid
from datetime import datetime

from app.core.executor import ExecutionStateStore


# Factory functions for test data
def create_execution_context(
    input_value: str = "test input",
    node_outputs: dict | None = None,
) -> dict:
    """Factory function to create execution context."""
    context = {"input": input_value}
    if node_outputs:
        context.update(node_outputs)
    return context


def create_execution_id() -> str:
    """Factory function to create execution ID."""
    return str(uuid.uuid4())


# Use the state_store fixture from conftest.py instead of creating a new one


class TestSaveState:
    """Test ExecutionStateStore.save_state method."""

    @pytest.mark.asyncio
    async def test_save_state_success(self, state_store):
        """Test saving execution state successfully."""
        execution_id = create_execution_id()
        current_node = "node-1"
        context = create_execution_context(
            input_value="test input",
            node_outputs={"previous": "output"},
        )

        # Save state
        await state_store.save_state(
            execution_id=execution_id,
            current_node=current_node,
            context=context,
        )

        # Verify it was saved
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None
        assert loaded["current_node"] == current_node
        assert loaded["context"]["input"] == "test input"
        assert loaded["context"]["previous"] == "output"

    @pytest.mark.asyncio
    async def test_save_state_replaces_existing(self, state_store):
        """Test that saving state replaces existing state (INSERT OR REPLACE)."""
        execution_id = create_execution_id()

        # Save initial state
        context1 = create_execution_context(input_value="first")
        await state_store.save_state(
            execution_id=execution_id,
            current_node="node-1",
            context=context1,
        )

        # Save updated state with same execution_id
        context2 = create_execution_context(
            input_value="second",
            node_outputs={"node-1": "output"},
        )
        await state_store.save_state(
            execution_id=execution_id,
            current_node="node-2",
            context=context2,
        )

        # Should have the updated state
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None
        assert loaded["current_node"] == "node-2"
        assert loaded["context"]["input"] == "second"
        assert loaded["context"]["node-1"] == "output"

    @pytest.mark.asyncio
    async def test_save_state_with_complex_context(self, state_store):
        """Test saving state with complex nested context."""
        execution_id = create_execution_id()
        context = create_execution_context(
            input_value="complex test",
            node_outputs={
                "node-1": {"result": "data", "count": 42},
                "node-2": ["item1", "item2", "item3"],
                "node-3": True,
            },
        )

        await state_store.save_state(
            execution_id=execution_id,
            current_node="node-4",
            context=context,
        )

        # Verify complex data is preserved
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None
        assert loaded["context"]["node-1"]["result"] == "data"
        assert loaded["context"]["node-1"]["count"] == 42
        assert loaded["context"]["node-2"] == ["item1", "item2", "item3"]
        assert loaded["context"]["node-3"] is True

    @pytest.mark.asyncio
    async def test_save_multiple_executions(self, state_store):
        """Test saving states for multiple executions."""
        exec_id_1 = create_execution_id()
        exec_id_2 = create_execution_id()

        context1 = create_execution_context(input_value="exec 1")
        context2 = create_execution_context(input_value="exec 2")

        await state_store.save_state(exec_id_1, "node-1", context1)
        await state_store.save_state(exec_id_2, "node-2", context2)

        # Both should exist independently
        loaded1 = await state_store.load_state(exec_id_1)
        loaded2 = await state_store.load_state(exec_id_2)

        assert loaded1["current_node"] == "node-1"
        assert loaded2["current_node"] == "node-2"
        assert loaded1["context"]["input"] == "exec 1"
        assert loaded2["context"]["input"] == "exec 2"


class TestLoadState:
    """Test ExecutionStateStore.load_state method."""

    @pytest.mark.asyncio
    async def test_load_state_exists(self, state_store):
        """Test loading existing state."""
        execution_id = create_execution_id()
        context = create_execution_context(
            input_value="test",
            node_outputs={"node-1": "result"},
        )

        await state_store.save_state(execution_id, "node-2", context)

        loaded = await state_store.load_state(execution_id)

        assert loaded is not None
        assert loaded["current_node"] == "node-2"
        assert loaded["context"]["input"] == "test"
        assert loaded["context"]["node-1"] == "result"

    @pytest.mark.asyncio
    async def test_load_state_not_exists(self, state_store):
        """Test loading non-existent state returns None."""
        fake_execution_id = create_execution_id()

        loaded = await state_store.load_state(fake_execution_id)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_state_after_delete(self, state_store):
        """Test loading state after deletion returns None."""
        execution_id = create_execution_id()
        context = create_execution_context()

        await state_store.save_state(execution_id, "node-1", context)
        await state_store.delete_state(execution_id)

        loaded = await state_store.load_state(execution_id)

        assert loaded is None


class TestMarkFailed:
    """Test ExecutionStateStore.mark_failed method."""

    @pytest.mark.asyncio
    async def test_mark_failed_updates_status(self, state_store):
        """Test marking execution as failed."""
        execution_id = create_execution_id()
        context = create_execution_context()

        # Save initial state
        await state_store.save_state(execution_id, "node-1", context)

        # Mark as failed
        error_message = "Node execution failed due to timeout"
        await state_store.mark_failed(
            execution_id=execution_id,
            node_id="node-1",
            error=error_message,
        )

        # Verify state still exists (mark_failed doesn't delete)
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_mark_failed_nonexistent_execution(self, state_store):
        """Test marking non-existent execution as failed (should not raise)."""
        fake_execution_id = create_execution_id()

        # Should not raise error
        await state_store.mark_failed(
            execution_id=fake_execution_id,
            node_id="node-1",
            error="Test error",
        )


class TestDeleteState:
    """Test ExecutionStateStore.delete_state method."""

    @pytest.mark.asyncio
    async def test_delete_state_success(self, state_store):
        """Test deleting execution state."""
        execution_id = create_execution_id()
        context = create_execution_context()

        # Save state
        await state_store.save_state(execution_id, "node-1", context)

        # Verify it exists
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None

        # Delete it
        await state_store.delete_state(execution_id)

        # Verify it's gone
        loaded_after_delete = await state_store.load_state(execution_id)
        assert loaded_after_delete is None

    @pytest.mark.asyncio
    async def test_delete_state_nonexistent(self, state_store):
        """Test deleting non-existent state (should not raise)."""
        fake_execution_id = create_execution_id()

        # Should not raise error
        await state_store.delete_state(fake_execution_id)

    @pytest.mark.asyncio
    async def test_delete_state_multiple_times(self, state_store):
        """Test deleting same state multiple times."""
        execution_id = create_execution_id()
        context = create_execution_context()

        await state_store.save_state(execution_id, "node-1", context)
        await state_store.delete_state(execution_id)

        # Delete again (should not raise)
        await state_store.delete_state(execution_id)

        loaded = await state_store.load_state(execution_id)
        assert loaded is None


class TestStateLifecycle:
    """Test complete state lifecycle: save -> load -> update -> delete."""

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self, state_store):
        """Test complete state lifecycle."""
        execution_id = create_execution_id()

        # 1. Save initial state
        context1 = create_execution_context(
            input_value="start",
            node_outputs={"node-1": "result1"},
        )
        await state_store.save_state(execution_id, "node-1", context1)

        # 2. Load and verify
        loaded1 = await state_store.load_state(execution_id)
        assert loaded1["current_node"] == "node-1"

        # 3. Update state (progress to next node)
        context2 = create_execution_context(
            input_value="start",
            node_outputs={
                "node-1": "result1",
                "node-2": "result2",
            },
        )
        await state_store.save_state(execution_id, "node-2", context2)

        # 4. Load updated state
        loaded2 = await state_store.load_state(execution_id)
        assert loaded2["current_node"] == "node-2"
        assert "node-2" in loaded2["context"]

        # 5. Delete state (cleanup after completion)
        await state_store.delete_state(execution_id)

        # 6. Verify deletion
        loaded3 = await state_store.load_state(execution_id)
        assert loaded3 is None

    @pytest.mark.asyncio
    async def test_lifecycle_with_failure(self, state_store):
        """Test state lifecycle when execution fails."""
        execution_id = create_execution_id()

        # Save state
        context = create_execution_context()
        await state_store.save_state(execution_id, "node-3", context)

        # Mark as failed
        await state_store.mark_failed(
            execution_id,
            "node-3",
            "Execution failed",
        )

        # State should still be loadable for recovery
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None

        # Manual cleanup
        await state_store.delete_state(execution_id)

        loaded_after = await state_store.load_state(execution_id)
        assert loaded_after is None


class TestConcurrentOperations:
    """Test concurrent state operations."""

    @pytest.mark.asyncio
    async def test_concurrent_saves_same_execution(self, state_store):
        """Test concurrent saves to same execution (last write wins)."""
        import asyncio

        execution_id = create_execution_id()

        async def save_state(node_id: str):
            context = create_execution_context(node_outputs={node_id: f"output-{node_id}"})
            await state_store.save_state(execution_id, node_id, context)

        # Save multiple states concurrently
        await asyncio.gather(
            save_state("node-1"),
            save_state("node-2"),
            save_state("node-3"),
        )

        # One of them should have won
        loaded = await state_store.load_state(execution_id)
        assert loaded is not None
        assert loaded["current_node"] in ["node-1", "node-2", "node-3"]

    @pytest.mark.asyncio
    async def test_concurrent_operations_different_executions(self, state_store):
        """Test concurrent operations on different executions."""
        import asyncio

        exec_ids = [create_execution_id() for _ in range(3)]

        async def handle_execution(exec_id: str, node_id: str):
            context = create_execution_context(input_value=f"input-{exec_id}")
            await state_store.save_state(exec_id, node_id, context)
            return await state_store.load_state(exec_id)

        # Concurrent operations on different executions
        results = await asyncio.gather(
            handle_execution(exec_ids[0], "node-1"),
            handle_execution(exec_ids[1], "node-2"),
            handle_execution(exec_ids[2], "node-3"),
        )

        # All should succeed
        assert all(r is not None for r in results)
        assert results[0]["current_node"] == "node-1"
        assert results[1]["current_node"] == "node-2"
        assert results[2]["current_node"] == "node-3"
