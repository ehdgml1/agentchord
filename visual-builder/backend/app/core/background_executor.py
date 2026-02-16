"""Background execution manager for async workflow dispatch.

SCALING NOTE: This implementation stores events and subscribers in-memory.
For horizontal scaling across multiple workers/instances, migrate to Redis:

1. Replace self._events dict with Redis STREAM or LIST
   - Use XADD for event publishing
   - Use XREAD/XRANGE for event retrieval
   - Automatic TTL via Redis expiration

2. Replace self._subscribers dict with Redis PUB/SUB
   - Publish events via PUBLISH command
   - WebSocket clients subscribe via SUBSCRIBE
   - Persistent across worker restarts

3. Use Redis for execution state tracking instead of in-memory dict
   - Track running tasks with HSET execution:{id} status running
   - Support distributed task cancellation

See: https://redis.io/docs/data-types/streams/
     https://redis.io/docs/interact/pubsub/
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Configuration
MAX_EVENTS_PER_EXECUTION = 1000
EVENT_TTL_SECONDS = 3600  # 1 hour


@dataclass
class ExecutionEvent:
    """Event emitted during execution."""
    execution_id: str
    event_type: str  # "started", "node_started", "node_completed", "completed", "failed"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class BackgroundExecutionManager:
    """Manages background workflow execution tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._events: dict[str, list[ExecutionEvent]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._event_timestamps: dict[str, datetime] = {}

    async def dispatch(
        self,
        execution_fn,
        execution_id: str,
    ) -> None:
        """Dispatch execution as background task."""
        # Cleanup stale events before dispatching new work
        self._cleanup_stale_events()

        task = asyncio.create_task(self._run(execution_fn, execution_id))
        self._tasks[execution_id] = task
        self._events[execution_id] = []
        self._event_timestamps[execution_id] = datetime.now(UTC)
        self._emit(execution_id, "started", {})

    async def _run(self, execution_fn, execution_id: str) -> None:
        """Run execution and track results."""
        try:
            result = await execution_fn()
            self._emit(execution_id, "completed", {"status": "completed"})
        except Exception as e:
            logger.exception("Background execution %s failed", execution_id)
            self._emit(execution_id, "failed", {"error": str(e)})
        finally:
            self._tasks.pop(execution_id, None)

    def _emit(self, execution_id: str, event_type: str, data: dict) -> None:
        """Emit event to subscribers."""
        event = ExecutionEvent(execution_id=execution_id, event_type=event_type, data=data)
        if execution_id not in self._events:
            self._events[execution_id] = []

        events = self._events[execution_id]
        # Enforce max events per execution
        if len(events) >= MAX_EVENTS_PER_EXECUTION:
            # Keep last half when limit reached
            self._events[execution_id] = events[len(events) // 2:]

        self._events[execution_id].append(event)
        self._event_timestamps[execution_id] = datetime.now(UTC)

        for queue in self._subscribers.get(execution_id, []):
            queue.put_nowait(event)

    def subscribe(self, execution_id: str) -> asyncio.Queue:
        """Subscribe to execution events."""
        queue: asyncio.Queue = asyncio.Queue()
        if execution_id not in self._subscribers:
            self._subscribers[execution_id] = []
        self._subscribers[execution_id].append(queue)
        return queue

    def unsubscribe(self, execution_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from execution events."""
        if execution_id in self._subscribers:
            self._subscribers[execution_id] = [q for q in self._subscribers[execution_id] if q is not queue]
            # Clean up empty subscriber lists
            if not self._subscribers[execution_id]:
                del self._subscribers[execution_id]

    def is_running(self, execution_id: str) -> bool:
        """Check if execution is still running."""
        return execution_id in self._tasks

    def get_events(self, execution_id: str) -> list[ExecutionEvent]:
        """Get all events for an execution."""
        return self._events.get(execution_id, [])

    def _cleanup_stale_events(self) -> None:
        """Remove events older than TTL for completed executions."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=EVENT_TTL_SECONDS)
        stale_ids = [
            eid for eid, ts in self._event_timestamps.items()
            if ts < cutoff and eid not in self._tasks
        ]
        for eid in stale_ids:
            self._events.pop(eid, None)
            self._subscribers.pop(eid, None)
            self._event_timestamps.pop(eid, None)

    async def shutdown(self) -> None:
        """Gracefully shutdown all running tasks."""
        if not self._tasks:
            return

        logger.info("Shutting down %d background tasks", len(self._tasks))

        # Cancel all running tasks
        for execution_id, task in list(self._tasks.items()):
            task.cancel()
            self._emit(execution_id, "failed", {"error": "Server shutting down"})

        # Wait for all tasks to complete (with timeout)
        tasks = list(self._tasks.values())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("All background tasks shut down")
