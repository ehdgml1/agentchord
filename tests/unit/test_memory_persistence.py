"""Integration tests for memory persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentweave.memory.base import MemoryEntry
from agentweave.memory.conversation import ConversationMemory
from agentweave.memory.stores import JSONFileStore, SQLiteStore

# Check if aiosqlite is available
try:
    import aiosqlite

    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class TestConversationMemoryWithJSONStore:
    """Tests for ConversationMemory with JSONFileStore."""

    @pytest.mark.asyncio
    async def test_auto_persist_on_add(self, tmp_path: Path) -> None:
        """Should automatically persist entries when added."""
        store = JSONFileStore(tmp_path)
        memory = ConversationMemory(store=store, namespace="session_1")

        # Add entries
        memory.add(MemoryEntry(content="Message 1"))
        memory.add(MemoryEntry(content="Message 2"))

        # Give async task time to complete
        import asyncio
        await asyncio.sleep(0.1)

        # Verify persistence
        entries = await store.load("session_1")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_load_from_store(self, tmp_path: Path) -> None:
        """Should load entries from store on startup."""
        store = JSONFileStore(tmp_path)

        # Create first memory and save data
        memory1 = ConversationMemory(store=store, namespace="session_1")
        memory1.add(MemoryEntry(content="Message 1"))
        memory1.add(MemoryEntry(content="Message 2"))
        memory1.add(MemoryEntry(content="Message 3"))
        await memory1.save_to_store()

        # Create new memory and load
        memory2 = ConversationMemory(store=store, namespace="session_1")
        count = await memory2.load_from_store()

        assert count == 3
        assert len(memory2) == 3
        assert memory2.get_recent()[0].content == "Message 1"

    @pytest.mark.asyncio
    async def test_save_to_store(self, tmp_path: Path) -> None:
        """Should save all entries to store."""
        store = JSONFileStore(tmp_path)
        memory = ConversationMemory(store=store, namespace="session_1")

        memory.add(MemoryEntry(content="A"))
        memory.add(MemoryEntry(content="B"))
        memory.add(MemoryEntry(content="C"))

        count = await memory.save_to_store()

        assert count == 3

        entries = await store.load("session_1")
        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, tmp_path: Path) -> None:
        """Should isolate different namespaces."""
        store = JSONFileStore(tmp_path)

        memory1 = ConversationMemory(store=store, namespace="session_1")
        memory2 = ConversationMemory(store=store, namespace="session_2")

        memory1.add(MemoryEntry(content="Session 1 message"))
        memory2.add(MemoryEntry(content="Session 2 message"))

        await memory1.save_to_store()
        await memory2.save_to_store()

        # Load into fresh memories
        memory1_new = ConversationMemory(store=store, namespace="session_1")
        memory2_new = ConversationMemory(store=store, namespace="session_2")

        await memory1_new.load_from_store()
        await memory2_new.load_from_store()

        assert len(memory1_new) == 1
        assert len(memory2_new) == 1
        assert memory1_new.get_recent()[0].content == "Session 1 message"
        assert memory2_new.get_recent()[0].content == "Session 2 message"

    @pytest.mark.asyncio
    async def test_max_entries_on_load(self, tmp_path: Path) -> None:
        """Should respect max_entries when loading."""
        store = JSONFileStore(tmp_path)

        # Save 10 entries
        memory1 = ConversationMemory(store=store, namespace="session_1")
        for i in range(10):
            memory1.add(MemoryEntry(content=f"Message {i}"))
        await memory1.save_to_store()

        # Load with smaller max_entries
        memory2 = ConversationMemory(max_entries=5, store=store, namespace="session_1")
        count = await memory2.load_from_store()

        assert count == 10  # Total available
        assert len(memory2) == 5  # Only recent 5 loaded
        assert memory2.get_recent()[0].content == "Message 5"
        assert memory2.get_recent()[-1].content == "Message 9"

    @pytest.mark.asyncio
    async def test_no_store_behavior(self, tmp_path: Path) -> None:
        """Should handle no store gracefully."""
        memory = ConversationMemory()

        memory.add(MemoryEntry(content="Test"))

        # Should return 0 without errors
        count = await memory.load_from_store()
        assert count == 0

        count = await memory.save_to_store()
        assert count == 0

    @pytest.mark.asyncio
    async def test_round_trip_preservation(self, tmp_path: Path) -> None:
        """Should preserve all entry fields through save/load."""
        store = JSONFileStore(tmp_path)

        memory1 = ConversationMemory(store=store, namespace="session_1")
        entry = MemoryEntry(
            content="Test message",
            role="assistant",
            metadata={"model": "gpt-4", "tokens": 100},
        )
        memory1.add(entry)
        await memory1.save_to_store()

        memory2 = ConversationMemory(store=store, namespace="session_1")
        await memory2.load_from_store()

        loaded = memory2.get(entry.id)
        assert loaded is not None
        assert loaded.content == entry.content
        assert loaded.role == entry.role
        assert loaded.metadata == entry.metadata


@pytest.mark.skipif(not AIOSQLITE_AVAILABLE, reason="aiosqlite not installed")
class TestConversationMemoryWithSQLiteStore:
    """Tests for ConversationMemory with SQLiteStore."""

    @pytest.mark.asyncio
    async def test_auto_persist_on_add(self) -> None:
        """Should automatically persist entries when added."""
        store = SQLiteStore(":memory:")
        memory = ConversationMemory(store=store, namespace="session_1")

        # Add entries
        memory.add(MemoryEntry(content="Message 1"))

        # Wait for first save
        import asyncio
        await asyncio.sleep(0.05)

        memory.add(MemoryEntry(content="Message 2"))

        # Wait for second save
        await asyncio.sleep(0.05)

        # Verify persistence
        entries = await store.load("session_1")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_load_from_store(self) -> None:
        """Should load entries from store on startup."""
        store = SQLiteStore(":memory:")

        # Create first memory and save data explicitly
        memory1 = ConversationMemory(store=store, namespace="session_1")
        memory1.add(MemoryEntry(content="Message 1"))
        memory1.add(MemoryEntry(content="Message 2"))
        memory1.add(MemoryEntry(content="Message 3"))

        # Wait briefly for any auto-persist tasks to complete before save_to_store
        import asyncio
        await asyncio.sleep(0.1)

        await memory1.save_to_store()

        # Create new memory with SAME store instance and load
        memory2 = ConversationMemory(store=store, namespace="session_1")
        count = await memory2.load_from_store()

        assert count == 3
        assert len(memory2) == 3

    @pytest.mark.asyncio
    async def test_file_persistence(self, tmp_path: Path) -> None:
        """Should persist across different store instances."""
        db_path = tmp_path / "memory.db"

        # Save with first store
        store1 = SQLiteStore(db_path)
        memory1 = ConversationMemory(store=store1, namespace="session_1")
        memory1.add(MemoryEntry(content="Persisted"))
        await memory1.save_to_store()

        # Load with new store
        store2 = SQLiteStore(db_path)
        memory2 = ConversationMemory(store=store2, namespace="session_1")
        await memory2.load_from_store()

        assert len(memory2) == 1
        assert memory2.get_recent()[0].content == "Persisted"

    @pytest.mark.asyncio
    async def test_concurrent_namespaces(self) -> None:
        """Should handle multiple namespaces concurrently."""
        store = SQLiteStore(":memory:")

        memories = [
            ConversationMemory(store=store, namespace=f"session_{i}")
            for i in range(5)
        ]

        # Add entries and save explicitly
        for i, memory in enumerate(memories):
            memory.add(MemoryEntry(content=f"Session {i} message"))
            await memory.save_to_store()

        # Verify isolation using SAME store instance
        for i in range(5):
            memory_new = ConversationMemory(store=store, namespace=f"session_{i}")
            await memory_new.load_from_store()
            assert len(memory_new) == 1
            assert memory_new.get_recent()[0].content == f"Session {i} message"


class TestMemoryStoreAbstraction:
    """Tests for store abstraction and polymorphism."""

    @pytest.mark.asyncio
    async def test_store_interface_compatibility(self, tmp_path: Path) -> None:
        """Both stores should work identically with ConversationMemory."""
        stores = [
            JSONFileStore(tmp_path / "json"),
        ]

        if AIOSQLITE_AVAILABLE:
            stores.append(SQLiteStore(tmp_path / "sqlite.db"))

        for i, store in enumerate(stores):
            memory = ConversationMemory(store=store, namespace="test")

            # Add entries
            memory.add(MemoryEntry(content="Message 1"))
            memory.add(MemoryEntry(content="Message 2"))
            await memory.save_to_store()

            # Load in new memory
            memory2 = ConversationMemory(store=store, namespace="test")
            await memory2.load_from_store()

            assert len(memory2) == 2
            assert memory2.get_recent()[0].content == "Message 1"
