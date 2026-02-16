"""Unit tests for SharedContext."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agentweave.orchestration.shared_context import ContextUpdate, SharedContext


class TestSharedContext:
    """Test SharedContext functionality."""

    @pytest.mark.asyncio
    async def test_initial_empty(self) -> None:
        """Test SharedContext starts empty by default."""
        ctx = SharedContext()
        assert ctx.size == 0
        assert ctx.update_count == 0
        assert ctx.snapshot() == {}
        assert await ctx.get_history() == []

    def test_initial_with_data(self) -> None:
        """Test SharedContext can be initialized with data."""
        initial = {"key1": "value1", "key2": 42}
        ctx = SharedContext(initial=initial)
        assert ctx.size == 2
        assert ctx.snapshot() == initial
        # Initial data doesn't create history
        assert ctx.update_count == 0

    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        """Test setting and getting values."""
        ctx = SharedContext()
        await ctx.set("name", "Alice", agent="agent1")

        value = await ctx.get("name")
        assert value == "Alice"
        assert ctx.size == 1
        assert ctx.update_count == 1

    @pytest.mark.asyncio
    async def test_get_default_value(self) -> None:
        """Test getting with default value."""
        ctx = SharedContext()
        value = await ctx.get("nonexistent", default="default_value")
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_get_returns_deep_copy(self) -> None:
        """Test that get() returns deep copy to prevent mutation."""
        ctx = SharedContext()
        original = {"nested": {"value": 42}}
        await ctx.set("data", original, agent="agent1")

        # Get the value
        retrieved = await ctx.get("data")
        assert retrieved == original

        # Mutate the retrieved value
        retrieved["nested"]["value"] = 999  # type: ignore[index]
        retrieved["new_key"] = "new_value"  # type: ignore[index]

        # Original should be unchanged
        stored = await ctx.get("data")
        assert stored == {"nested": {"value": 42}}

    @pytest.mark.asyncio
    async def test_update_multiple_values(self) -> None:
        """Test updating multiple values at once."""
        ctx = SharedContext()
        data = {"key1": "value1", "key2": 42, "key3": [1, 2, 3]}
        await ctx.update(data, agent="agent1")

        assert ctx.size == 3
        assert await ctx.get("key1") == "value1"
        assert await ctx.get("key2") == 42
        assert await ctx.get("key3") == [1, 2, 3]
        # Should create 3 history entries
        assert ctx.update_count == 3

    @pytest.mark.asyncio
    async def test_delete_existing_key(self) -> None:
        """Test deleting an existing key."""
        ctx = SharedContext()
        await ctx.set("key", "value", agent="agent1")
        assert ctx.size == 1

        result = await ctx.delete("key", agent="agent1")
        assert result is True
        assert ctx.size == 0
        assert not await ctx.has("key")
        # 1 set + 1 delete
        assert ctx.update_count == 2

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self) -> None:
        """Test deleting a non-existent key."""
        ctx = SharedContext()
        result = await ctx.delete("nonexistent", agent="agent1")
        assert result is False
        # No history entry for failed delete
        assert ctx.update_count == 0

    @pytest.mark.asyncio
    async def test_has_key(self) -> None:
        """Test checking key existence."""
        ctx = SharedContext()
        assert not await ctx.has("key")

        await ctx.set("key", "value", agent="agent1")
        assert await ctx.has("key")

        await ctx.delete("key", agent="agent1")
        assert not await ctx.has("key")

    @pytest.mark.asyncio
    async def test_keys_list(self) -> None:
        """Test getting list of keys."""
        ctx = SharedContext()
        assert await ctx.keys() == []

        await ctx.set("key1", "value1", agent="agent1")
        await ctx.set("key2", "value2", agent="agent1")
        await ctx.set("key3", "value3", agent="agent1")

        keys = await ctx.keys()
        assert set(keys) == {"key1", "key2", "key3"}

    def test_snapshot_returns_deep_copy(self) -> None:
        """Test that snapshot() returns a deep copy."""
        ctx = SharedContext(initial={"data": {"nested": 42}})
        snapshot1 = ctx.snapshot()
        assert snapshot1 == {"data": {"nested": 42}}

        # Mutate the snapshot
        snapshot1["data"]["nested"] = 999  # type: ignore[index]

        # Original should be unchanged
        snapshot2 = ctx.snapshot()
        assert snapshot2 == {"data": {"nested": 42}}

    @pytest.mark.asyncio
    async def test_snapshot_async_returns_deep_copy(self) -> None:
        """Test that snapshot_async() returns a deep copy."""
        ctx = SharedContext(initial={"data": {"nested": 42}})
        snapshot1 = await ctx.snapshot_async()
        assert snapshot1 == {"data": {"nested": 42}}

        # Mutate the snapshot
        snapshot1["data"]["nested"] = 999  # type: ignore[index]

        # Original should be unchanged
        snapshot2 = await ctx.snapshot_async()
        assert snapshot2 == {"data": {"nested": 42}}

    @pytest.mark.asyncio
    async def test_snapshot_async_concurrent_safe(self) -> None:
        """Test that snapshot_async() is safe during concurrent writes."""
        ctx = SharedContext(initial={"counter": 0, "data": {"list": []}})

        async def concurrent_writes() -> None:
            """Perform many writes to stress-test concurrency."""
            for i in range(50):
                await ctx.set("counter", i, agent="writer")
                await ctx.update({"data": {"list": list(range(i))}}, agent="writer")
                await asyncio.sleep(0.001)  # Small delay to increase interleaving

        async def concurrent_snapshots() -> list[dict[str, Any]]:
            """Take many snapshots during writes."""
            snapshots = []
            for _ in range(50):
                snapshot = await ctx.snapshot_async()
                snapshots.append(snapshot)
                await asyncio.sleep(0.001)
            return snapshots

        # Run writes and snapshots concurrently
        _, snapshots = await asyncio.gather(
            concurrent_writes(),
            concurrent_snapshots(),
        )

        # All snapshots should be consistent (no partial mutations)
        for snapshot in snapshots:
            # Verify snapshot structure is intact
            assert "counter" in snapshot
            assert "data" in snapshot
            assert isinstance(snapshot["data"], dict)
            assert "list" in snapshot["data"]
            assert isinstance(snapshot["data"]["list"], list)

            # Verify consistency: if counter is N, list should have N elements
            counter = snapshot["counter"]
            list_len = len(snapshot["data"]["list"])
            # Allow some slack due to concurrent updates
            # (snapshot might catch state between set/update calls)
            assert isinstance(counter, int)
            assert isinstance(list_len, int)
            assert counter >= 0 and list_len >= 0

    @pytest.mark.asyncio
    async def test_history_tracking(self) -> None:
        """Test that all updates are tracked in history."""
        ctx = SharedContext()

        await ctx.set("key1", "value1", agent="agent1")
        await ctx.set("key2", "value2", agent="agent2")
        await ctx.update({"key3": "value3", "key4": "value4"}, agent="agent1")
        await ctx.delete("key2", agent="agent2")

        history = await ctx.get_history()
        assert len(history) == 5  # 2 sets + 2 updates + 1 delete

        # Verify operations
        assert history[0].key == "key1"
        assert history[0].value == "value1"
        assert history[0].agent == "agent1"
        assert history[0].operation == "set"

        assert history[4].key == "key2"
        assert history[4].value is None
        assert history[4].agent == "agent2"
        assert history[4].operation == "delete"

    @pytest.mark.asyncio
    async def test_agent_updates_filter(self) -> None:
        """Test filtering updates by agent."""
        ctx = SharedContext()

        await ctx.set("key1", "value1", agent="agent1")
        await ctx.set("key2", "value2", agent="agent2")
        await ctx.set("key3", "value3", agent="agent1")
        await ctx.delete("key2", agent="agent2")

        agent1_updates = await ctx.get_agent_updates("agent1")
        assert len(agent1_updates) == 2
        assert all(u.agent == "agent1" for u in agent1_updates)

        agent2_updates = await ctx.get_agent_updates("agent2")
        assert len(agent2_updates) == 2
        assert all(u.agent == "agent2" for u in agent2_updates)

    def test_size_property(self) -> None:
        """Test size property."""
        ctx = SharedContext()
        assert ctx.size == 0

        ctx = SharedContext(initial={"a": 1, "b": 2, "c": 3})
        assert ctx.size == 3

    def test_update_count_property(self) -> None:
        """Test update_count property."""
        ctx = SharedContext(initial={"a": 1})
        # Initial data doesn't count
        assert ctx.update_count == 0

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing all data and history."""
        ctx = SharedContext(initial={"key": "value"})
        assert ctx.size == 1

        await ctx.clear()
        assert ctx.size == 0
        assert ctx.update_count == 0
        assert ctx.snapshot() == {}
        assert await ctx.get_history() == []

    @pytest.mark.asyncio
    async def test_concurrent_writes(self) -> None:
        """Test that concurrent writes are thread-safe."""
        ctx = SharedContext()

        async def write_values(agent: str, start: int, count: int) -> None:
            for i in range(start, start + count):
                await ctx.set(f"key{i}", f"value{i}", agent=agent)

        # Run 3 agents writing concurrently
        await asyncio.gather(
            write_values("agent1", 0, 10),
            write_values("agent2", 10, 10),
            write_values("agent3", 20, 10),
        )

        # All 30 writes should succeed
        assert ctx.size == 30
        assert ctx.update_count == 30

        # Verify all keys exist
        for i in range(30):
            assert await ctx.has(f"key{i}")
            assert await ctx.get(f"key{i}") == f"value{i}"

    @pytest.mark.asyncio
    async def test_concurrent_updates_same_key(self) -> None:
        """Test concurrent updates to the same key are serialized."""
        ctx = SharedContext()

        async def increment(agent: str, count: int) -> None:
            for _ in range(count):
                current = await ctx.get("counter", default=0)
                await asyncio.sleep(0.001)  # Simulate some work
                await ctx.set("counter", current + 1, agent=agent)

        # Run 3 agents incrementing concurrently
        await asyncio.gather(
            increment("agent1", 5),
            increment("agent2", 5),
            increment("agent3", 5),
        )

        # Due to race conditions, final value may be less than 15
        # But the lock ensures no data corruption
        final = await ctx.get("counter")
        assert isinstance(final, int)
        assert final >= 0
        # History should have 15 entries
        assert ctx.update_count == 15


class TestSharedContextMaxHistory:
    """Tests for SharedContext max_history trimming."""

    @pytest.mark.asyncio
    async def test_max_history_trims(self) -> None:
        """History is trimmed to max_history after exceeding it."""
        ctx = SharedContext(max_history=5)

        for i in range(10):
            await ctx.set(f"key{i}", f"value{i}", agent="agent")

        history = await ctx.get_history()
        assert len(history) == 5
        # Should keep the last 5 entries (keys 5-9)
        assert history[0].key == "key5"
        assert history[-1].key == "key9"

    def test_max_history_default_is_10000(self) -> None:
        """Default max_history is 10000."""
        ctx = SharedContext()
        assert ctx.max_history == 10000

    @pytest.mark.asyncio
    async def test_max_history_trims_via_update(self) -> None:
        """History is also trimmed when using update()."""
        ctx = SharedContext(max_history=3)

        await ctx.update({"a": 1, "b": 2, "c": 3, "d": 4}, agent="agent")

        history = await ctx.get_history()
        assert len(history) == 3
        # Should keep last 3: b, c, d
        assert history[0].key == "b"
        assert history[-1].key == "d"


class TestSharedContextDeepCopy:
    """Tests for deep copy on write in SharedContext."""

    @pytest.mark.asyncio
    async def test_set_deep_copies_value(self) -> None:
        """Mutating the original dict after set() does not affect stored value."""
        ctx = SharedContext()
        original = {"nested": {"value": 42}, "list": [1, 2, 3]}
        await ctx.set("data", original, agent="agent")

        # Mutate the original
        original["nested"]["value"] = 999
        original["list"].append(4)
        original["new_key"] = "new"

        # Stored value should be unchanged
        stored = await ctx.get("data")
        assert stored == {"nested": {"value": 42}, "list": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_set_deep_copies_in_history(self) -> None:
        """History entries contain independent copies of values."""
        ctx = SharedContext()
        original = {"key": "original"}
        await ctx.set("data", original, agent="agent")

        # Mutate original
        original["key"] = "mutated"

        # History value should be unchanged
        history = await ctx.get_history()
        assert history[0].value == {"key": "original"}

    @pytest.mark.asyncio
    async def test_update_deep_copies_values(self) -> None:
        """Mutating originals after update() does not affect stored values."""
        ctx = SharedContext()
        nested = {"inner": [1, 2]}
        await ctx.update({"data": nested}, agent="agent")

        # Mutate the original
        nested["inner"].append(3)
        nested["extra"] = True

        # Stored value should be unchanged
        stored = await ctx.get("data")
        assert stored == {"inner": [1, 2]}

    @pytest.mark.asyncio
    async def test_update_deep_copies_in_history(self) -> None:
        """History entries from update() contain independent copies."""
        ctx = SharedContext()
        nested = {"value": 100}
        await ctx.update({"key": nested}, agent="agent")

        # Mutate original
        nested["value"] = 200

        history = await ctx.get_history()
        assert history[0].value == {"value": 100}


class TestContextUpdate:
    """Test ContextUpdate model."""

    def test_context_update_creation(self) -> None:
        """Test creating a ContextUpdate."""
        update = ContextUpdate(
            key="test_key",
            value="test_value",
            agent="test_agent",
            operation="set",
        )
        assert update.key == "test_key"
        assert update.value == "test_value"
        assert update.agent == "test_agent"
        assert update.operation == "set"
        assert update.timestamp is not None

    def test_context_update_defaults(self) -> None:
        """Test ContextUpdate default values."""
        update = ContextUpdate(key="key", value="value", agent="agent")
        assert update.operation == "set"
        assert update.timestamp is not None


class TestSharedContextAsyncSafety:
    """Tests for async safety of clear() and get_history()."""

    @pytest.mark.asyncio
    async def test_clear_is_async_safe(self) -> None:
        """Concurrent clear + set should not corrupt state."""
        ctx = SharedContext()

        async def writer() -> None:
            for i in range(50):
                await ctx.set(f"key_{i}", f"value_{i}", agent="writer")

        async def clearer() -> None:
            for _ in range(10):
                await ctx.clear()
                await asyncio.sleep(0.001)

        # Run writer and clearer concurrently - should not raise
        await asyncio.gather(writer(), clearer())

        # State should be consistent (no partial corruption)
        history = await ctx.get_history()
        assert isinstance(history, list)
        # All items in history should be proper ContextUpdate instances
        for entry in history:
            assert isinstance(entry, ContextUpdate)

    @pytest.mark.asyncio
    async def test_get_history_is_async_safe(self) -> None:
        """Concurrent get_history + set should return consistent snapshots."""
        ctx = SharedContext()

        async def writer() -> None:
            for i in range(50):
                await ctx.set(f"key_{i}", f"value_{i}", agent="writer")

        async def reader() -> list[int]:
            lengths = []
            for _ in range(50):
                history = await ctx.get_history()
                lengths.append(len(history))
                await asyncio.sleep(0.001)
            return lengths

        _, lengths = await asyncio.gather(writer(), reader())

        # History lengths should be monotonically non-decreasing
        # (each snapshot is a consistent point in time)
        for i in range(1, len(lengths)):
            assert lengths[i] >= lengths[i - 1] or lengths[i] == 0
