"""Working memory implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from agentchord.memory.base import BaseMemory, MemoryEntry


class WorkingItem(BaseModel):
    """Item in working memory with expiration."""

    key: str
    value: Any
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None
    priority: int = 0  # Higher = more important

    @property
    def is_expired(self) -> bool:
        """Check if item has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class WorkingMemory(BaseMemory):
    """Working memory for temporary task-specific context.

    Stores key-value pairs with optional expiration.
    Useful for maintaining context during multi-step operations.

    Example:
        >>> memory = WorkingMemory(default_ttl=300)  # 5 minute TTL
        >>> memory.set("current_file", "/path/to/file.py")
        >>> memory.set("step", 1)
        >>> file = memory.get_value("current_file")
        >>> memory.increment("step")
    """

    def __init__(
        self,
        default_ttl: float | None = None,
        max_items: int = 100,
    ) -> None:
        """Initialize working memory.

        Args:
            default_ttl: Default time-to-live in seconds (None = no expiration).
            max_items: Maximum number of items to store.
        """
        self._default_ttl = default_ttl
        self._max_items = max_items
        self._items: dict[str, WorkingItem] = {}
        self._entries: dict[str, MemoryEntry] = {}  # For BaseMemory interface

    @property
    def default_ttl(self) -> float | None:
        """Default TTL in seconds."""
        return self._default_ttl

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        priority: int = 0,
    ) -> None:
        """Set a value in working memory.

        Args:
            key: The key to store under.
            value: The value to store.
            ttl: Time-to-live in seconds (None uses default_ttl).
            priority: Priority for eviction (higher = kept longer).
        """
        self._cleanup_expired()

        # Evict if at capacity
        if len(self._items) >= self._max_items and key not in self._items:
            self._evict_one()

        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = None
        if effective_ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=effective_ttl)

        self._items[key] = WorkingItem(
            key=key,
            value=value,
            expires_at=expires_at,
            priority=priority,
        )

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a value from working memory.

        Args:
            key: The key to look up.
            default: Default value if key not found or expired.

        Returns:
            The stored value or default.
        """
        item = self._items.get(key)
        if item is None or item.is_expired:
            return default
        return item.value

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        item = self._items.get(key)
        return item is not None and not item.is_expired

    def remove(self, key: str) -> bool:
        """Remove a key from working memory.

        Returns:
            True if key existed and was removed.
        """
        if key in self._items:
            del self._items[key]
            return True
        return False

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value.

        Args:
            key: The key to increment.
            amount: Amount to add.

        Returns:
            New value after increment.

        Raises:
            KeyError: If key doesn't exist.
            TypeError: If value is not numeric.
        """
        item = self._items.get(key)
        if item is None or item.is_expired:
            raise KeyError(f"Key not found: {key}")

        if not isinstance(item.value, (int, float)):
            raise TypeError(f"Cannot increment non-numeric value: {type(item.value)}")

        new_value = item.value + amount
        self.set(key, new_value, priority=item.priority)
        return new_value

    def keys(self) -> list[str]:
        """Get all non-expired keys."""
        self._cleanup_expired()
        return list(self._items.keys())

    def values(self) -> list[Any]:
        """Get all non-expired values."""
        self._cleanup_expired()
        return [item.value for item in self._items.values()]

    def items(self) -> list[tuple[str, Any]]:
        """Get all non-expired key-value pairs."""
        self._cleanup_expired()
        return [(k, item.value) for k, item in self._items.items()]

    # BaseMemory interface implementation
    def add(self, entry: MemoryEntry) -> None:
        """Add entry (stores in both formats)."""
        self._entries[entry.id] = entry
        self.set(entry.id, entry.content)

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Get entry by ID."""
        return self._entries.get(entry_id)

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get most recent entries."""
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return sorted_entries[:limit]

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search entries by substring."""
        query_lower = query.lower()
        results = [
            entry for entry in self._entries.values()
            if query_lower in entry.content.lower()
        ]
        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
        self._entries.clear()

    def __len__(self) -> int:
        """Return number of non-expired items."""
        self._cleanup_expired()
        return len(self._items)

    def _cleanup_expired(self) -> None:
        """Remove expired items."""
        expired_keys = [
            key for key, item in self._items.items()
            if item.is_expired
        ]
        for key in expired_keys:
            del self._items[key]

    def _evict_one(self) -> None:
        """Evict one item (lowest priority, oldest)."""
        if not self._items:
            return

        # Sort by priority (asc) then by created_at (asc)
        to_evict = min(
            self._items.values(),
            key=lambda item: (item.priority, item.created_at),
        )
        del self._items[to_evict.key]
