"""Tests for debug executor."""
import pytest
import asyncio
import uuid
from datetime import datetime

from app.core.debug_executor import (
    DebugExecutor,
    DebugSession,
    DebugEventType,
    DebugEvent,
)


# Factory functions for test data
def create_workflow_data(node_count: int = 3) -> dict:
    """Factory function to create workflow data."""
    nodes = []
    for i in range(node_count):
        nodes.append({
            "id": f"node-{i+1}",
            "type": "agent",
            "data": {
                "name": f"Agent {i+1}",
                "role": f"Process step {i+1}",
            },
        })

    return {"nodes": nodes}


def create_debug_session() -> DebugSession:
    """Factory function to create debug session."""
    return DebugSession()


def create_debug_executor(
    workflow_data: dict | None = None,
    session: DebugSession | None = None,
) -> DebugExecutor:
    """Factory function to create debug executor."""
    if workflow_data is None:
        workflow_data = create_workflow_data()
    if session is None:
        session = create_debug_session()

    return DebugExecutor(workflow_data, session)


class TestDebugSession:
    """Test DebugSession functionality."""

    @pytest.mark.asyncio
    async def test_session_wait_timeout(self):
        """Test session wait timeout after inactivity."""
        session = create_debug_session()

        # Wait with very short timeout
        with pytest.raises(asyncio.TimeoutError):
            await session.wait_for_command(timeout=0.1)

        # Session should be stopped after timeout
        assert session.is_stopped

    @pytest.mark.asyncio
    async def test_session_continue(self):
        """Test continue command."""
        session = create_debug_session()

        # Queue continue command
        session.continue_()

        # Should receive continue
        cmd = await session.wait_for_command(timeout=1.0)
        assert cmd == "continue"
        assert not session.is_stopped

    @pytest.mark.asyncio
    async def test_session_step(self):
        """Test step command."""
        session = create_debug_session()

        # Queue step command
        session.step()

        # Should receive step
        cmd = await session.wait_for_command(timeout=1.0)
        assert cmd == "step"
        assert not session.is_stopped

    @pytest.mark.asyncio
    async def test_session_stop(self):
        """Test stop command."""
        session = create_debug_session()

        # Queue stop command
        session.stop()

        # Should receive stop and be stopped
        cmd = await session.wait_for_command(timeout=1.0)
        assert cmd == "stop"
        assert session.is_stopped

    @pytest.mark.asyncio
    async def test_session_multiple_commands(self):
        """Test queuing multiple commands."""
        session = create_debug_session()

        # Queue multiple commands
        session.step()
        session.continue_()
        session.step()

        # Should receive in order
        assert await session.wait_for_command(timeout=1.0) == "step"
        assert await session.wait_for_command(timeout=1.0) == "continue"
        assert await session.wait_for_command(timeout=1.0) == "step"

    def test_session_is_stopped_initial_state(self):
        """Test initial stopped state is False."""
        session = create_debug_session()
        assert not session.is_stopped

    def test_session_inactivity_timeout_constant(self):
        """Test inactivity timeout is set correctly."""
        assert DebugSession.INACTIVITY_TIMEOUT == 600


class TestDebugExecutor:
    """Test DebugExecutor functionality."""

    @pytest.mark.asyncio
    async def test_run_debug_emits_events(self):
        """Test debug execution emits correct events."""
        workflow_data = create_workflow_data(node_count=2)
        session = create_debug_session()
        executor = create_debug_executor(workflow_data, session)

        events = []

        # Collect events
        async for event in executor.run_debug():
            events.append(event)

        # Should have: 2x NODE_START, 2x NODE_COMPLETE, 1x COMPLETE
        assert len(events) == 5

        # Check event types
        assert events[0].type == DebugEventType.NODE_START
        assert events[1].type == DebugEventType.NODE_COMPLETE
        assert events[2].type == DebugEventType.NODE_START
        assert events[3].type == DebugEventType.NODE_COMPLETE
        assert events[4].type == DebugEventType.COMPLETE

    @pytest.mark.asyncio
    async def test_breakpoint_pauses_execution(self):
        """Test breakpoint causes execution to pause."""
        workflow_data = create_workflow_data(node_count=3)
        session = create_debug_session()

        # Set breakpoint on node-2
        session._breakpoints.add("node-2")

        executor = create_debug_executor(workflow_data, session)

        events = []
        breakpoint_hit = False

        async def collect_events():
            nonlocal breakpoint_hit
            async for event in executor.run_debug():
                events.append(event)
                if event.type == DebugEventType.BREAKPOINT:
                    breakpoint_hit = True
                    # Continue after breakpoint
                    session.continue_()

        await collect_events()

        # Should have hit breakpoint
        assert breakpoint_hit
        # Should have BREAKPOINT event
        breakpoint_events = [e for e in events if e.type == DebugEventType.BREAKPOINT]
        assert len(breakpoint_events) == 1
        assert breakpoint_events[0].node_id == "node-2"

    @pytest.mark.asyncio
    async def test_stop_command_halts_execution(self):
        """Test stop command halts execution."""
        workflow_data = create_workflow_data(node_count=5)
        session = create_debug_session()

        # Set breakpoint on node-2
        session._breakpoints.add("node-2")

        executor = create_debug_executor(workflow_data, session)

        events = []

        async def collect_events():
            async for event in executor.run_debug():
                events.append(event)
                if event.type == DebugEventType.BREAKPOINT:
                    # Stop instead of continuing
                    session.stop()

        await collect_events()

        # Should not complete all 5 nodes
        node_complete_events = [
            e for e in events if e.type == DebugEventType.NODE_COMPLETE
        ]
        assert len(node_complete_events) < 5

        # Should not have COMPLETE event
        complete_events = [e for e in events if e.type == DebugEventType.COMPLETE]
        assert len(complete_events) == 0

    @pytest.mark.asyncio
    async def test_node_execution_stores_results(self):
        """Test node execution stores results."""
        workflow_data = create_workflow_data(node_count=2)
        session = create_debug_session()
        executor = create_debug_executor(workflow_data, session)

        async for event in executor.run_debug():
            if event.type == DebugEventType.COMPLETE:
                # Check results are stored
                assert "results" in event.data
                results = event.data["results"]
                assert "node-1" in results
                assert "node-2" in results

    @pytest.mark.asyncio
    async def test_timeout_event_on_inactivity(self):
        """Test timeout event is emitted on inactivity."""
        workflow_data = create_workflow_data(node_count=2)
        session = create_debug_session()

        # Set breakpoint on first node
        session._breakpoints.add("node-1")

        executor = create_debug_executor(workflow_data, session)

        events = []

        async def collect_events():
            async for event in executor.run_debug():
                events.append(event)
                # Don't send any commands, let it timeout
                if event.type == DebugEventType.BREAKPOINT:
                    # Wait for timeout
                    pass

        # Use short timeout for test
        session.INACTIVITY_TIMEOUT = 0.1

        await collect_events()

        # Should have timeout event
        timeout_events = [e for e in events if e.type == DebugEventType.TIMEOUT]
        assert len(timeout_events) == 1

    @pytest.mark.asyncio
    async def test_error_event_on_node_failure(self):
        """Test error event on node execution failure."""
        workflow_data = create_workflow_data(node_count=2)
        session = create_debug_session()
        executor = create_debug_executor(workflow_data, session)

        # Mock _execute_node to raise exception
        original_execute = executor._execute_node

        async def failing_execute(node):
            if node["id"] == "node-2":
                raise ValueError("Test error")
            return await original_execute(node)

        executor._execute_node = failing_execute

        events = []

        async for event in executor.run_debug():
            events.append(event)

        # Should have error event
        error_events = [e for e in events if e.type == DebugEventType.ERROR]
        assert len(error_events) >= 1
        assert error_events[0].node_id == "node-2"
        assert "Test error" in error_events[0].data["error"]


class TestDebugEvent:
    """Test DebugEvent dataclass."""

    def test_create_debug_event_minimal(self):
        """Test creating debug event with minimal fields."""
        event = DebugEvent(
            type=DebugEventType.NODE_START,
            node_id="node-1",
        )

        assert event.type == DebugEventType.NODE_START
        assert event.node_id == "node-1"
        assert event.data == {}
        assert event.timestamp is not None

    def test_create_debug_event_full(self):
        """Test creating debug event with all fields."""
        event = DebugEvent(
            type=DebugEventType.BREAKPOINT,
            node_id="node-2",
            data={"test": "value"},
            timestamp="2024-01-01T00:00:00",
        )

        assert event.type == DebugEventType.BREAKPOINT
        assert event.node_id == "node-2"
        assert event.data["test"] == "value"
        assert event.timestamp == "2024-01-01T00:00:00"

    def test_debug_event_types_enum(self):
        """Test all debug event types are defined."""
        expected_types = {
            "BREAKPOINT",
            "NODE_START",
            "NODE_COMPLETE",
            "COMPLETE",
            "ERROR",
            "TIMEOUT",
        }

        actual_types = {e.name for e in DebugEventType}
        assert actual_types == expected_types


class TestDebugExecutorIntegration:
    """Integration tests for debug executor."""

    @pytest.mark.asyncio
    async def test_full_workflow_execution(self):
        """Test complete workflow execution in debug mode."""
        workflow_data = create_workflow_data(node_count=3)
        session = create_debug_session()
        executor = create_debug_executor(workflow_data, session)

        events = []
        async for event in executor.run_debug():
            events.append(event)

        # Verify complete execution
        assert len(events) == 7  # 3x START, 3x COMPLETE, 1x COMPLETE
        assert events[-1].type == DebugEventType.COMPLETE
        assert events[-1].data["nodes_executed"] == 3

    @pytest.mark.asyncio
    async def test_multiple_breakpoints(self):
        """Test execution with multiple breakpoints."""
        workflow_data = create_workflow_data(node_count=4)
        session = create_debug_session()

        # Set multiple breakpoints
        session._breakpoints.add("node-1")
        session._breakpoints.add("node-3")

        executor = create_debug_executor(workflow_data, session)

        breakpoints_hit = []

        async def collect_events():
            async for event in executor.run_debug():
                if event.type == DebugEventType.BREAKPOINT:
                    breakpoints_hit.append(event.node_id)
                    session.continue_()

        await collect_events()

        # Should hit both breakpoints
        assert len(breakpoints_hit) == 2
        assert "node-1" in breakpoints_hit
        assert "node-3" in breakpoints_hit

    @pytest.mark.asyncio
    async def test_step_through_workflow(self):
        """Test stepping through workflow one node at a time."""
        workflow_data = create_workflow_data(node_count=3)
        session = create_debug_session()

        # Set breakpoint on each node
        session._breakpoints.add("node-1")
        session._breakpoints.add("node-2")
        session._breakpoints.add("node-3")

        executor = create_debug_executor(workflow_data, session)

        node_starts = []

        async def collect_events():
            async for event in executor.run_debug():
                if event.type == DebugEventType.NODE_START:
                    node_starts.append(event.node_id)
                elif event.type == DebugEventType.BREAKPOINT:
                    # Step to next node
                    session.step()

        await collect_events()

        # Should execute all nodes in order
        assert node_starts == ["node-1", "node-2", "node-3"]
