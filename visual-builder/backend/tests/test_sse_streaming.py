"""Tests for Server-Sent Events (SSE) execution streaming."""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from app.core.background_executor import BackgroundExecutionManager, ExecutionEvent
from datetime import datetime, UTC


@pytest.mark.asyncio
async def test_sse_stream_existing_events():
    """Test SSE stream returns existing events."""
    bg_executor = BackgroundExecutionManager()
    execution_id = "test-exec-1"

    # Add some existing events
    bg_executor._events[execution_id] = [
        ExecutionEvent(
            execution_id=execution_id,
            event_type="started",
            data={},
            timestamp=datetime.now(UTC),
        ),
        ExecutionEvent(
            execution_id=execution_id,
            event_type="node_started",
            data={"node_id": "node1"},
            timestamp=datetime.now(UTC),
        ),
    ]

    # Get events
    events = bg_executor.get_events(execution_id)
    assert len(events) == 2
    assert events[0].event_type == "started"
    assert events[1].event_type == "node_started"
    assert events[1].data["node_id"] == "node1"


@pytest.mark.asyncio
async def test_sse_stream_live_events():
    """Test SSE stream receives live events."""
    bg_executor = BackgroundExecutionManager()
    execution_id = "test-exec-2"

    # Subscribe before starting execution
    queue = bg_executor.subscribe(execution_id)
    collected_events = []

    # Start execution
    async def mock_execution():
        await asyncio.sleep(0.1)
        bg_executor._emit(execution_id, "node_started", {"node_id": "node1"})
        await asyncio.sleep(0.1)
        bg_executor._emit(execution_id, "node_completed", {"node_id": "node1", "output": "success"})

    await bg_executor.dispatch(mock_execution, execution_id)

    try:
        # Collect events with timeout
        for _ in range(5):  # Max 5 events
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                collected_events.append(event)
                if event.event_type == "completed":
                    break
            except asyncio.TimeoutError:
                break

        # Verify we got the events
        assert len(collected_events) >= 3  # started, node_started, node_completed, completed
        event_types = [e.event_type for e in collected_events]
        assert "started" in event_types
        assert "node_started" in event_types

    finally:
        bg_executor.unsubscribe(execution_id, queue)


@pytest.mark.asyncio
async def test_sse_stream_is_running():
    """Test SSE stream detects running state correctly."""
    bg_executor = BackgroundExecutionManager()
    execution_id = "test-exec-3"

    # Before dispatch - not running
    assert not bg_executor.is_running(execution_id)

    # Start execution
    async def long_execution():
        await asyncio.sleep(0.5)

    await bg_executor.dispatch(long_execution, execution_id)

    # During execution - running
    assert bg_executor.is_running(execution_id)

    # Wait for completion
    await asyncio.sleep(0.6)

    # After completion - not running
    assert not bg_executor.is_running(execution_id)


@pytest.mark.asyncio
async def test_sse_stream_multiple_subscribers():
    """Test SSE stream supports multiple subscribers."""
    bg_executor = BackgroundExecutionManager()
    execution_id = "test-exec-4"

    # Create multiple subscribers
    queue1 = bg_executor.subscribe(execution_id)
    queue2 = bg_executor.subscribe(execution_id)

    # Emit event
    bg_executor._emit(execution_id, "test_event", {"data": "test"})

    # Both queues should receive the event
    event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

    assert event1.event_type == "test_event"
    assert event2.event_type == "test_event"
    assert event1.data["data"] == "test"
    assert event2.data["data"] == "test"

    # Cleanup
    bg_executor.unsubscribe(execution_id, queue1)
    bg_executor.unsubscribe(execution_id, queue2)


@pytest.mark.asyncio
async def test_sse_stream_unsubscribe():
    """Test SSE stream unsubscribe works correctly."""
    bg_executor = BackgroundExecutionManager()
    execution_id = "test-exec-5"

    # Subscribe
    queue = bg_executor.subscribe(execution_id)
    assert len(bg_executor._subscribers.get(execution_id, [])) == 1

    # Unsubscribe
    bg_executor.unsubscribe(execution_id, queue)
    assert len(bg_executor._subscribers.get(execution_id, [])) == 0


@pytest.mark.asyncio
async def test_sse_stream_failed_execution():
    """Test SSE stream handles failed executions."""
    bg_executor = BackgroundExecutionManager()
    execution_id = "test-exec-6"

    # Subscribe before starting execution
    queue = bg_executor.subscribe(execution_id)
    collected_events = []

    # Start execution that fails
    async def failing_execution():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")

    await bg_executor.dispatch(failing_execution, execution_id)

    try:
        # Collect events
        for _ in range(3):
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                collected_events.append(event)
                if event.event_type == "failed":
                    break
            except asyncio.TimeoutError:
                break

        # Verify we got failure event
        assert len(collected_events) >= 2  # started, failed
        event_types = [e.event_type for e in collected_events]
        assert "started" in event_types
        assert "failed" in event_types

        # Check error data
        failed_event = next(e for e in collected_events if e.event_type == "failed")
        assert "error" in failed_event.data

    finally:
        bg_executor.unsubscribe(execution_id, queue)
