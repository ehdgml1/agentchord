"""Abstract interface for memory persistence backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentweave.memory.base import MemoryEntry


class MemoryStore(ABC):
    """Abstract interface for memory persistence backends.

    All storage backends must implement these async operations
    for saving, loading, and managing memory entries.
    """

    @abstractmethod
    async def save(self, namespace: str, entry: MemoryEntry) -> None:
        """Save a single entry to persistent storage.

        Args:
            namespace: Logical grouping for entries (e.g., agent_id, session_id).
            entry: Memory entry to save.
        """
        ...

    @abstractmethod
    async def save_many(self, namespace: str, entries: list[MemoryEntry]) -> None:
        """Save multiple entries to persistent storage.

        Args:
            namespace: Logical grouping for entries.
            entries: Memory entries to save.
        """
        ...

    @abstractmethod
    async def load(self, namespace: str) -> list[MemoryEntry]:
        """Load all entries for a namespace.

        Args:
            namespace: Namespace to load entries from.

        Returns:
            List of memory entries, in no guaranteed order.
        """
        ...

    @abstractmethod
    async def delete(self, namespace: str, entry_id: str) -> bool:
        """Delete an entry by ID.

        Args:
            namespace: Namespace containing the entry.
            entry_id: Entry ID to delete.

        Returns:
            True if entry was deleted, False if not found.
        """
        ...

    @abstractmethod
    async def clear(self, namespace: str) -> None:
        """Clear all entries for a namespace.

        Args:
            namespace: Namespace to clear.
        """
        ...

    @abstractmethod
    async def count(self, namespace: str) -> int:
        """Count entries in a namespace.

        Args:
            namespace: Namespace to count entries in.

        Returns:
            Number of entries in the namespace.
        """
        ...
