"""Thread-safe shared context for multi-agent collaboration.

Provides a shared key-value store that multiple agents can read from
and write to safely during concurrent execution.
"""
from __future__ import annotations

import asyncio
import copy
from collections import deque
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ContextUpdate(BaseModel):
    """Record of a context modification."""

    key: str
    value: Any
    agent: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    operation: str = "set"  # "set" or "delete"


class SharedContext:
    """Thread-safe shared state for multi-agent collaboration.

    Agents can safely read and write to shared context during concurrent
    execution. All modifications are tracked in a history log.

    Example:
        >>> ctx = SharedContext(initial={"topic": "AI agents"})
        >>> await ctx.set("findings", "...", agent="researcher")
        >>> value = await ctx.get("findings")
        >>> history = await ctx.get_history()
    """

    def __init__(
        self,
        initial: dict[str, Any] | None = None,
        max_history: int = 10000,
    ) -> None:
        self._data: dict[str, Any] = dict(initial) if initial else {}
        self._lock = asyncio.Lock()
        self._history: deque[ContextUpdate] = deque(
            maxlen=max_history if max_history > 0 else None,
        )
        self._max_history = max_history

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from shared context."""
        async with self._lock:
            value = self._data.get(key, default)
            # Return deep copy to prevent mutation
            return copy.deepcopy(value)

    async def set(self, key: str, value: Any, agent: str = "") -> None:
        """Set a value in shared context."""
        async with self._lock:
            self._data[key] = copy.deepcopy(value)
            self._history.append(
                ContextUpdate(
                    key=key, value=copy.deepcopy(value), agent=agent, operation="set",
                )
            )

    async def update(self, data: dict[str, Any], agent: str = "") -> None:
        """Update multiple values at once."""
        async with self._lock:
            for key, value in data.items():
                self._data[key] = copy.deepcopy(value)
                self._history.append(
                    ContextUpdate(
                        key=key,
                        value=copy.deepcopy(value),
                        agent=agent,
                        operation="set",
                    )
                )

    async def delete(self, key: str, agent: str = "") -> bool:
        """Delete a key from shared context. Returns True if key existed."""
        async with self._lock:
            if key in self._data:
                del self._data[key]
                self._history.append(
                    ContextUpdate(key=key, value=None, agent=agent, operation="delete")
                )
                return True
            return False

    async def has(self, key: str) -> bool:
        """Check if a key exists."""
        async with self._lock:
            return key in self._data

    async def keys(self) -> list[str]:
        """Get all keys."""
        async with self._lock:
            return list(self._data.keys())

    def snapshot(self) -> dict[str, Any]:
        """Return an immutable deep copy of current state.

        Warning: This is synchronous for convenience in non-async contexts,
        but is NOT concurrency-safe. If called concurrently with async
        set()/update()/delete(), the deep copy could read a partially-mutated
        dictionary. Use snapshot_async() for concurrency-safe snapshots.
        """
        return copy.deepcopy(self._data)

    async def snapshot_async(self) -> dict[str, Any]:
        """Return an async-safe immutable deep copy of current state.

        This method acquires the lock before deep copying, ensuring
        no partial mutations can be observed during concurrent writes.
        """
        async with self._lock:
            return copy.deepcopy(self._data)

    async def get_history(self) -> list[ContextUpdate]:
        """Return all context updates in chronological order."""
        async with self._lock:
            return list(self._history)

    async def get_agent_updates(self, agent: str) -> list[ContextUpdate]:
        """Return updates made by a specific agent."""
        async with self._lock:
            return [u for u in self._history if u.agent == agent]

    @property
    def size(self) -> int:
        """Number of keys in context."""
        return len(self._data)

    @property
    def update_count(self) -> int:
        """Total number of updates made."""
        return len(self._history)

    @property
    def max_history(self) -> int:
        """Maximum number of history entries."""
        return self._max_history

    async def clear(self) -> None:
        """Clear all data and history."""
        async with self._lock:
            self._data.clear()
            self._history.clear()
