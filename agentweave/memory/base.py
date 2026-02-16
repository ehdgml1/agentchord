"""Base memory interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """Single memory entry."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    role: str = "user"  # user, assistant, system
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)


class BaseMemory(ABC):
    """Abstract base class for memory implementations.

    All memory types must implement add, get, search, and clear operations.
    """

    @abstractmethod
    def add(self, entry: MemoryEntry) -> None:
        """Add an entry to memory."""
        ...

    @abstractmethod
    def get(self, entry_id: str) -> MemoryEntry | None:
        """Get entry by ID."""
        ...

    @abstractmethod
    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get most recent entries."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search entries by query."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries."""
        ...

    @abstractmethod
    def __len__(self) -> int:
        """Return number of entries."""
        ...
