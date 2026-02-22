"""Conversation memory implementation."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING, Iterator

from agentchord.memory.base import BaseMemory, MemoryEntry

if TYPE_CHECKING:
    from agentchord.memory.stores.base import MemoryStore


class ConversationMemory(BaseMemory):
    """In-memory conversation history with sliding window.

    Maintains a bounded history of conversation turns with optional
    persistent storage backend.

    Example:
        >>> memory = ConversationMemory(max_entries=100)
        >>> memory.add(MemoryEntry(content="Hello", role="user"))
        >>> memory.add(MemoryEntry(content="Hi there!", role="assistant"))
        >>> len(memory)
        2

        >>> # With persistent storage
        >>> from agentchord.memory.stores import SQLiteStore
        >>> store = SQLiteStore("memory.db")
        >>> memory = ConversationMemory(max_entries=100, store=store, namespace="agent_1")
        >>> await memory.load_from_store()
    """

    def __init__(
        self,
        max_entries: int = 1000,
        store: MemoryStore | None = None,
        namespace: str = "default",
    ) -> None:
        """Initialize conversation memory.

        Args:
            max_entries: Maximum number of entries to keep (oldest removed first).
            store: Optional persistent storage backend.
            namespace: Namespace for persistent storage (e.g., agent_id, session_id).
        """
        self._max_entries = max_entries
        self._entries: deque[MemoryEntry] = deque(maxlen=max_entries)
        self._index: dict[str, MemoryEntry] = {}
        self._store = store
        self._namespace = namespace

    @property
    def max_entries(self) -> int:
        """Maximum number of entries."""
        return self._max_entries

    def add(self, entry: MemoryEntry) -> None:
        """Add entry to conversation history.

        If max_entries is reached, oldest entry is removed.
        If a store is configured, the entry is automatically persisted.
        """
        # Remove from index if we're at capacity and will evict
        if len(self._entries) == self._max_entries:
            oldest = self._entries[0]
            self._index.pop(oldest.id, None)

        self._entries.append(entry)
        self._index[entry.id] = entry

        # Persist to store if available
        if self._store:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._store.save(self._namespace, entry))
            except RuntimeError:
                # No event loop running, skip persistence
                pass

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Get entry by ID."""
        return self._index.get(entry_id)

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get most recent entries in chronological order."""
        entries = list(self._entries)
        return entries[-limit:] if limit < len(entries) else entries

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Simple substring search in entry content.

        For semantic search, use SemanticMemory instead.
        """
        query_lower = query.lower()
        results: list[MemoryEntry] = []

        # Search from most recent
        for entry in reversed(self._entries):
            if query_lower in entry.content.lower():
                results.append(entry)
                if len(results) >= limit:
                    break

        return results

    def clear(self) -> None:
        """Clear all conversation history."""
        self._entries.clear()
        self._index.clear()

    def __len__(self) -> int:
        """Return number of entries in memory."""
        return len(self._entries)

    def __iter__(self) -> Iterator[MemoryEntry]:
        """Iterate over entries in chronological order."""
        return iter(self._entries)

    def to_messages(self) -> list[dict[str, str]]:
        """Convert to LLM message format.

        Returns:
            List of {"role": ..., "content": ...} dicts.
        """
        return [
            {"role": entry.role, "content": entry.content}
            for entry in self._entries
        ]

    async def load_from_store(self) -> int:
        """Load entries from persistent store.

        Entries are loaded in chronological order, with only the most
        recent max_entries kept in memory.

        Returns:
            Number of entries loaded.

        Raises:
            RuntimeError: If no store is configured.
        """
        if not self._store:
            return 0

        entries = await self._store.load(self._namespace)

        # Sort by timestamp to ensure chronological order
        entries.sort(key=lambda e: e.timestamp)

        # Load only the most recent max_entries
        for entry in entries[-self._max_entries :]:
            self._entries.append(entry)
            self._index[entry.id] = entry

        return len(entries)

    async def save_to_store(self) -> int:
        """Save all current entries to persistent store.

        This replaces any existing entries in the store for this namespace.

        Returns:
            Number of entries saved.

        Raises:
            RuntimeError: If no store is configured.
        """
        if not self._store:
            return 0

        await self._store.save_many(self._namespace, list(self._entries))
        return len(self._entries)
