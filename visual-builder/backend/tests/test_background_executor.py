"""Tests for BackgroundExecutionManager."""
import asyncio
import pytest
from app.core.background_executor import BackgroundExecutionManager, ExecutionEvent, MAX_EVENTS_PER_EXECUTION


@pytest.mark.asyncio
async def test_dispatch_and_complete():
    mgr = BackgroundExecutionManager()
    async def fn(): return "done"
    await mgr.dispatch(fn, "exec-1")
    await asyncio.sleep(0.1)
    events = mgr.get_events("exec-1")
    assert len(events) >= 2
    assert events[0].event_type == "started"
    assert events[-1].event_type == "completed"


@pytest.mark.asyncio
async def test_dispatch_failure():
    mgr = BackgroundExecutionManager()
    async def fn(): raise ValueError("boom")
    await mgr.dispatch(fn, "exec-2")
    await asyncio.sleep(0.1)
    events = mgr.get_events("exec-2")
    assert events[-1].event_type == "failed"
    assert "boom" in events[-1].data["error"]


@pytest.mark.asyncio
async def test_subscribe_unsubscribe():
    mgr = BackgroundExecutionManager()
    queue = mgr.subscribe("exec-3")
    assert queue is not None
    mgr.unsubscribe("exec-3", queue)
    assert "exec-3" not in mgr._subscribers


@pytest.mark.asyncio
async def test_max_events_enforced():
    mgr = BackgroundExecutionManager()
    mgr._events["exec-4"] = []
    mgr._event_timestamps["exec-4"] = __import__("datetime").datetime.now(__import__("datetime").UTC)
    for i in range(MAX_EVENTS_PER_EXECUTION + 10):
        mgr._emit("exec-4", "node_completed", {"i": i})
    assert len(mgr._events["exec-4"]) <= MAX_EVENTS_PER_EXECUTION


@pytest.mark.asyncio
async def test_cleanup_stale():
    from datetime import timedelta, UTC, datetime
    mgr = BackgroundExecutionManager()
    mgr._events["old-exec"] = [ExecutionEvent("old-exec", "completed")]
    mgr._event_timestamps["old-exec"] = datetime.now(UTC) - timedelta(seconds=7200)
    mgr._cleanup_stale_events()
    assert "old-exec" not in mgr._events


@pytest.mark.asyncio
async def test_shutdown():
    mgr = BackgroundExecutionManager()
    async def slow(): await asyncio.sleep(10)
    await mgr.dispatch(slow, "exec-5")
    assert mgr.is_running("exec-5")
    await mgr.shutdown()
    assert not mgr.is_running("exec-5")
