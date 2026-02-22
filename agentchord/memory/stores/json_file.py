"""JSON file-based memory storage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from agentchord.memory.base import MemoryEntry
from agentchord.memory.stores.base import MemoryStore


class JSONFileStore(MemoryStore):
    """File-based memory storage using JSON.

    Stores entries as JSON files in a directory structure:
        base_dir/
            namespace1/
                entries.json
            namespace2/
                entries.json

    Example:
        >>> store = JSONFileStore("./memory_data")
        >>> await store.save("agent_1", entry)
        >>> entries = await store.load("agent_1")
    """

    def __init__(self, base_dir: str | Path) -> None:
        """Initialize JSON file store.

        Args:
            base_dir: Base directory for storing namespace folders.
        """
        self._base_dir = Path(base_dir)
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, namespace: str) -> asyncio.Lock:
        """Get or create lock for namespace."""
        if namespace not in self._locks:
            self._locks[namespace] = asyncio.Lock()
        return self._locks[namespace]

    @staticmethod
    def _validate_namespace(namespace: str) -> None:
        """Validate namespace to prevent path traversal attacks."""
        if not namespace or ".." in namespace or "/" in namespace or "\\" in namespace:
            raise ValueError(f"Invalid namespace: {namespace!r}")

    def _get_namespace_path(self, namespace: str) -> Path:
        """Get path to namespace directory."""
        self._validate_namespace(namespace)
        resolved = (self._base_dir / namespace).resolve()
        if not str(resolved).startswith(str(self._base_dir.resolve())):
            raise ValueError(f"Invalid namespace: {namespace!r}")
        return self._base_dir / namespace

    def _get_entries_path(self, namespace: str) -> Path:
        """Get path to entries.json file."""
        return self._get_namespace_path(namespace) / "entries.json"

    def _serialize_entry(self, entry: MemoryEntry) -> dict[str, Any]:
        """Serialize entry to dict with datetime handling."""
        data = entry.model_dump()
        # Convert datetime to ISO format string
        data["timestamp"] = entry.timestamp.isoformat()
        return data

    def _deserialize_entry(self, data: dict[str, Any]) -> MemoryEntry:
        """Deserialize entry from dict."""
        return MemoryEntry.model_validate(data)

    async def save(self, namespace: str, entry: MemoryEntry) -> None:
        """Save a single entry."""
        lock = self._get_lock(namespace)
        async with lock:
            # Load existing entries
            entries = await self._load_unlocked(namespace)

            # Replace or append entry
            existing_ids = {e.id for e in entries}
            if entry.id in existing_ids:
                entries = [e for e in entries if e.id != entry.id]

            entries.append(entry)

            # Write back
            await self._save_unlocked(namespace, entries)

    async def save_many(self, namespace: str, entries: list[MemoryEntry]) -> None:
        """Save multiple entries."""
        lock = self._get_lock(namespace)
        async with lock:
            await self._save_unlocked(namespace, entries)

    async def load(self, namespace: str) -> list[MemoryEntry]:
        """Load all entries for a namespace."""
        lock = self._get_lock(namespace)
        async with lock:
            return await self._load_unlocked(namespace)

    async def delete(self, namespace: str, entry_id: str) -> bool:
        """Delete an entry by ID."""
        lock = self._get_lock(namespace)
        async with lock:
            entries = await self._load_unlocked(namespace)
            original_count = len(entries)

            entries = [e for e in entries if e.id != entry_id]

            if len(entries) < original_count:
                await self._save_unlocked(namespace, entries)
                return True
            return False

    async def clear(self, namespace: str) -> None:
        """Clear all entries for a namespace."""
        lock = self._get_lock(namespace)
        async with lock:
            await self._save_unlocked(namespace, [])

    async def count(self, namespace: str) -> int:
        """Count entries in a namespace."""
        lock = self._get_lock(namespace)
        async with lock:
            entries = await self._load_unlocked(namespace)
            return len(entries)

    async def _load_unlocked(self, namespace: str) -> list[MemoryEntry]:
        """Load entries without locking (internal use)."""
        entries_path = self._get_entries_path(namespace)

        if not entries_path.exists():
            return []

        def _read_file() -> list[MemoryEntry]:
            with entries_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return [self._deserialize_entry(item) for item in data]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read_file)

    async def _save_unlocked(self, namespace: str, entries: list[MemoryEntry]) -> None:
        """Save entries without locking (internal use)."""
        namespace_path = self._get_namespace_path(namespace)
        entries_path = self._get_entries_path(namespace)

        # Create directory if needed
        def _write_file() -> None:
            namespace_path.mkdir(parents=True, exist_ok=True)
            data = [self._serialize_entry(e) for e in entries]
            with entries_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _write_file)
