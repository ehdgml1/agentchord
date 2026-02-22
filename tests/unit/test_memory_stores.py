"""Unit tests for memory storage backends."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agentchord.memory.base import MemoryEntry
from agentchord.memory.stores import JSONFileStore, MemoryStore, SQLiteStore

# Check if aiosqlite is available for SQLite tests
try:
    import aiosqlite

    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class TestJSONFileStore:
    """Tests for JSONFileStore."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, tmp_path: Path) -> None:
        """Should save and load entries."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(content="Hello", role="user")

        await store.save("agent_1", entry)

        entries = await store.load("agent_1")

        assert len(entries) == 1
        assert entries[0].content == "Hello"
        assert entries[0].id == entry.id

    @pytest.mark.asyncio
    async def test_save_many(self, tmp_path: Path) -> None:
        """Should save multiple entries."""
        store = JSONFileStore(tmp_path)
        entries = [
            MemoryEntry(content="A", role="user"),
            MemoryEntry(content="B", role="assistant"),
            MemoryEntry(content="C", role="user"),
        ]

        await store.save_many("agent_1", entries)

        loaded = await store.load("agent_1")

        assert len(loaded) == 3
        contents = {e.content for e in loaded}
        assert contents == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, tmp_path: Path) -> None:
        """Should isolate entries by namespace."""
        store = JSONFileStore(tmp_path)
        entry1 = MemoryEntry(content="Agent 1")
        entry2 = MemoryEntry(content="Agent 2")

        await store.save("agent_1", entry1)
        await store.save("agent_2", entry2)

        entries1 = await store.load("agent_1")
        entries2 = await store.load("agent_2")

        assert len(entries1) == 1
        assert len(entries2) == 1
        assert entries1[0].content == "Agent 1"
        assert entries2[0].content == "Agent 2"

    @pytest.mark.asyncio
    async def test_delete_entry(self, tmp_path: Path) -> None:
        """Should delete specific entry."""
        store = JSONFileStore(tmp_path)
        entry1 = MemoryEntry(content="Keep")
        entry2 = MemoryEntry(content="Delete")

        await store.save("agent_1", entry1)
        await store.save("agent_1", entry2)

        deleted = await store.delete("agent_1", entry2.id)

        assert deleted is True

        entries = await store.load("agent_1")
        assert len(entries) == 1
        assert entries[0].id == entry1.id

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Should return False for nonexistent entry."""
        store = JSONFileStore(tmp_path)

        deleted = await store.delete("agent_1", "nonexistent")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_namespace(self, tmp_path: Path) -> None:
        """Should clear all entries in namespace."""
        store = JSONFileStore(tmp_path)
        await store.save("agent_1", MemoryEntry(content="A"))
        await store.save("agent_1", MemoryEntry(content="B"))

        await store.clear("agent_1")

        entries = await store.load("agent_1")
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_count(self, tmp_path: Path) -> None:
        """Should count entries in namespace."""
        store = JSONFileStore(tmp_path)

        assert await store.count("agent_1") == 0

        await store.save("agent_1", MemoryEntry(content="A"))
        await store.save("agent_1", MemoryEntry(content="B"))

        assert await store.count("agent_1") == 2

    @pytest.mark.asyncio
    async def test_datetime_serialization(self, tmp_path: Path) -> None:
        """Should preserve datetime fields."""
        store = JSONFileStore(tmp_path)
        now = datetime.now()
        entry = MemoryEntry(content="Test", timestamp=now)

        await store.save("agent_1", entry)
        loaded = await store.load("agent_1")

        # Timestamps should be close (within 1 second)
        delta = abs((loaded[0].timestamp - now).total_seconds())
        assert delta < 1.0

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, tmp_path: Path) -> None:
        """Should preserve metadata."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(
            content="Test",
            metadata={"model": "gpt-4", "tokens": 100, "nested": {"key": "value"}},
        )

        await store.save("agent_1", entry)
        loaded = await store.load("agent_1")

        assert loaded[0].metadata == entry.metadata

    @pytest.mark.asyncio
    async def test_update_existing_entry(self, tmp_path: Path) -> None:
        """Should update existing entry when saved again."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(content="Original")

        await store.save("agent_1", entry)

        # Update content but keep same ID
        entry.content = "Updated"
        await store.save("agent_1", entry)

        entries = await store.load("agent_1")

        assert len(entries) == 1
        assert entries[0].content == "Updated"

    @pytest.mark.asyncio
    async def test_load_empty_namespace(self, tmp_path: Path) -> None:
        """Should return empty list for new namespace."""
        store = JSONFileStore(tmp_path)

        entries = await store.load("nonexistent")

        assert entries == []

    @pytest.mark.asyncio
    async def test_directory_creation(self, tmp_path: Path) -> None:
        """Should create directory structure automatically."""
        store = JSONFileStore(tmp_path / "nested" / "path")
        entry = MemoryEntry(content="Test")

        await store.save("agent_1", entry)

        assert (tmp_path / "nested" / "path" / "agent_1" / "entries.json").exists()


class TestJSONFileStorePathTraversal:
    """Tests for path traversal prevention in JSONFileStore."""

    @pytest.mark.asyncio
    async def test_rejects_dotdot_namespace(self, tmp_path: Path) -> None:
        """Should reject namespace with .. path traversal."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(content="Test")
        with pytest.raises(ValueError, match="Invalid namespace"):
            await store.save("../../etc", entry)

    @pytest.mark.asyncio
    async def test_rejects_slash_namespace(self, tmp_path: Path) -> None:
        """Should reject namespace with forward slashes."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(content="Test")
        with pytest.raises(ValueError, match="Invalid namespace"):
            await store.save("foo/bar", entry)

    @pytest.mark.asyncio
    async def test_rejects_empty_namespace(self, tmp_path: Path) -> None:
        """Should reject empty namespace."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(content="Test")
        with pytest.raises(ValueError, match="Invalid namespace"):
            await store.save("", entry)

    @pytest.mark.asyncio
    async def test_allows_valid_namespace(self, tmp_path: Path) -> None:
        """Should allow safe namespace names."""
        store = JSONFileStore(tmp_path)
        entry = MemoryEntry(content="Test")
        await store.save("agent_1", entry)
        entries = await store.load("agent_1")
        assert len(entries) == 1


@pytest.mark.skipif(not AIOSQLITE_AVAILABLE, reason="aiosqlite not installed")
class TestSQLiteStore:
    """Tests for SQLiteStore."""

    @pytest.mark.asyncio
    async def test_save_and_load(self) -> None:
        """Should save and load entries."""
        store = SQLiteStore(":memory:")
        entry = MemoryEntry(content="Hello", role="user")

        await store.save("agent_1", entry)

        entries = await store.load("agent_1")

        assert len(entries) == 1
        assert entries[0].content == "Hello"
        assert entries[0].id == entry.id

    @pytest.mark.asyncio
    async def test_save_many(self) -> None:
        """Should save multiple entries."""
        store = SQLiteStore(":memory:")
        entries = [
            MemoryEntry(content="A", role="user"),
            MemoryEntry(content="B", role="assistant"),
            MemoryEntry(content="C", role="user"),
        ]

        await store.save_many("agent_1", entries)

        loaded = await store.load("agent_1")

        assert len(loaded) == 3
        contents = {e.content for e in loaded}
        assert contents == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_namespace_isolation(self) -> None:
        """Should isolate entries by namespace."""
        store = SQLiteStore(":memory:")
        entry1 = MemoryEntry(content="Agent 1")
        entry2 = MemoryEntry(content="Agent 2")

        await store.save("agent_1", entry1)
        await store.save("agent_2", entry2)

        entries1 = await store.load("agent_1")
        entries2 = await store.load("agent_2")

        assert len(entries1) == 1
        assert len(entries2) == 1
        assert entries1[0].content == "Agent 1"
        assert entries2[0].content == "Agent 2"

    @pytest.mark.asyncio
    async def test_delete_entry(self) -> None:
        """Should delete specific entry."""
        store = SQLiteStore(":memory:")
        entry1 = MemoryEntry(content="Keep")
        entry2 = MemoryEntry(content="Delete")

        await store.save("agent_1", entry1)
        await store.save("agent_1", entry2)

        deleted = await store.delete("agent_1", entry2.id)

        assert deleted is True

        entries = await store.load("agent_1")
        assert len(entries) == 1
        assert entries[0].id == entry1.id

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self) -> None:
        """Should return False for nonexistent entry."""
        store = SQLiteStore(":memory:")

        deleted = await store.delete("agent_1", "nonexistent")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_namespace(self) -> None:
        """Should clear all entries in namespace."""
        store = SQLiteStore(":memory:")
        await store.save("agent_1", MemoryEntry(content="A"))
        await store.save("agent_1", MemoryEntry(content="B"))

        await store.clear("agent_1")

        entries = await store.load("agent_1")
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        """Should count entries in namespace."""
        store = SQLiteStore(":memory:")

        assert await store.count("agent_1") == 0

        await store.save("agent_1", MemoryEntry(content="A"))
        await store.save("agent_1", MemoryEntry(content="B"))

        assert await store.count("agent_1") == 2

    @pytest.mark.asyncio
    async def test_datetime_serialization(self) -> None:
        """Should preserve datetime fields."""
        store = SQLiteStore(":memory:")
        now = datetime.now()
        entry = MemoryEntry(content="Test", timestamp=now)

        await store.save("agent_1", entry)
        loaded = await store.load("agent_1")

        # Timestamps should be close (within 1 second)
        delta = abs((loaded[0].timestamp - now).total_seconds())
        assert delta < 1.0

    @pytest.mark.asyncio
    async def test_metadata_preservation(self) -> None:
        """Should preserve metadata."""
        store = SQLiteStore(":memory:")
        entry = MemoryEntry(
            content="Test",
            metadata={"model": "gpt-4", "tokens": 100, "nested": {"key": "value"}},
        )

        await store.save("agent_1", entry)
        loaded = await store.load("agent_1")

        assert loaded[0].metadata == entry.metadata

    @pytest.mark.asyncio
    async def test_update_existing_entry(self) -> None:
        """Should update existing entry when saved again."""
        store = SQLiteStore(":memory:")
        entry = MemoryEntry(content="Original")

        await store.save("agent_1", entry)

        # Update content but keep same ID
        entry.content = "Updated"
        await store.save("agent_1", entry)

        entries = await store.load("agent_1")

        assert len(entries) == 1
        assert entries[0].content == "Updated"

    @pytest.mark.asyncio
    async def test_load_empty_namespace(self) -> None:
        """Should return empty list for new namespace."""
        store = SQLiteStore(":memory:")

        entries = await store.load("nonexistent")

        assert entries == []

    @pytest.mark.asyncio
    async def test_chronological_order(self) -> None:
        """Should return entries in chronological order."""
        store = SQLiteStore(":memory:")
        base_time = datetime.now()

        entries = [
            MemoryEntry(content="First", timestamp=base_time),
            MemoryEntry(content="Second", timestamp=base_time + timedelta(seconds=1)),
            MemoryEntry(content="Third", timestamp=base_time + timedelta(seconds=2)),
        ]

        await store.save_many("agent_1", entries)

        loaded = await store.load("agent_1")

        assert loaded[0].content == "First"
        assert loaded[1].content == "Second"
        assert loaded[2].content == "Third"

    @pytest.mark.asyncio
    async def test_file_persistence(self, tmp_path: Path) -> None:
        """Should persist to file and reload."""
        db_path = tmp_path / "memory.db"

        # Save with first store
        store1 = SQLiteStore(db_path)
        await store1.save("agent_1", MemoryEntry(content="Persisted"))

        # Load with new store
        store2 = SQLiteStore(db_path)
        entries = await store2.load("agent_1")

        assert len(entries) == 1
        assert entries[0].content == "Persisted"

    @pytest.mark.asyncio
    async def test_save_many_replaces(self) -> None:
        """Should replace existing entries when using save_many."""
        store = SQLiteStore(":memory:")

        await store.save("agent_1", MemoryEntry(content="Old"))
        await store.save_many("agent_1", [MemoryEntry(content="New")])

        entries = await store.load("agent_1")

        assert len(entries) == 1
        assert entries[0].content == "New"


def test_sqlite_import_error() -> None:
    """Should raise ImportError when aiosqlite not available."""
    if AIOSQLITE_AVAILABLE:
        pytest.skip("aiosqlite is available")

    with pytest.raises(ImportError, match="aiosqlite is required"):
        SQLiteStore(":memory:")
