"""Unit tests for Memory module."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest

from agentweave.memory.base import BaseMemory, MemoryEntry
from agentweave.memory.conversation import ConversationMemory
from agentweave.memory.semantic import SemanticMemory, _cosine_similarity
from agentweave.memory.working import WorkingMemory, WorkingItem


class TestMemoryEntry:
    """Tests for MemoryEntry."""

    def test_entry_creation(self) -> None:
        """Entry should be created with defaults."""
        entry = MemoryEntry(content="Hello")

        assert entry.content == "Hello"
        assert entry.role == "user"
        assert entry.id is not None
        assert entry.timestamp is not None

    def test_entry_custom_fields(self) -> None:
        """Entry should accept custom fields."""
        entry = MemoryEntry(
            content="Hi there",
            role="assistant",
            metadata={"model": "gpt-4"},
        )

        assert entry.role == "assistant"
        assert entry.metadata["model"] == "gpt-4"

    def test_entry_hashable(self) -> None:
        """Entry should be hashable by ID."""
        entry1 = MemoryEntry(content="A")
        entry2 = MemoryEntry(content="A")

        # Different IDs, different hash
        assert hash(entry1) != hash(entry2)

        # Can be used in sets
        entries = {entry1, entry2}
        assert len(entries) == 2


class TestConversationMemory:
    """Tests for ConversationMemory."""

    def test_add_and_get(self) -> None:
        """Should add and retrieve entries."""
        memory = ConversationMemory()
        entry = MemoryEntry(content="Hello")

        memory.add(entry)

        assert memory.get(entry.id) == entry
        assert len(memory) == 1

    def test_get_recent(self) -> None:
        """Should return recent entries in order."""
        memory = ConversationMemory()

        for i in range(5):
            memory.add(MemoryEntry(content=f"Message {i}"))

        recent = memory.get_recent(limit=3)

        assert len(recent) == 3
        assert recent[0].content == "Message 2"
        assert recent[2].content == "Message 4"

    def test_sliding_window(self) -> None:
        """Should evict oldest when max reached."""
        memory = ConversationMemory(max_entries=3)

        for i in range(5):
            memory.add(MemoryEntry(content=f"Message {i}"))

        assert len(memory) == 3
        # Oldest (0, 1) should be evicted
        assert memory.get_recent()[0].content == "Message 2"

    def test_search_substring(self) -> None:
        """Should find entries containing query."""
        memory = ConversationMemory()
        memory.add(MemoryEntry(content="The weather is nice"))
        memory.add(MemoryEntry(content="How are you?"))
        memory.add(MemoryEntry(content="Nice to meet you"))

        results = memory.search("nice")

        assert len(results) == 2

    def test_clear(self) -> None:
        """Should clear all entries."""
        memory = ConversationMemory()
        memory.add(MemoryEntry(content="Hello"))

        memory.clear()

        assert len(memory) == 0

    def test_to_messages(self) -> None:
        """Should convert to LLM message format."""
        memory = ConversationMemory()
        memory.add(MemoryEntry(content="Hello", role="user"))
        memory.add(MemoryEntry(content="Hi!", role="assistant"))

        messages = memory.to_messages()

        assert messages == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

    def test_iteration(self) -> None:
        """Should be iterable."""
        memory = ConversationMemory()
        memory.add(MemoryEntry(content="A"))
        memory.add(MemoryEntry(content="B"))

        contents = [e.content for e in memory]

        assert contents == ["A", "B"]


class TestSemanticMemory:
    """Tests for SemanticMemory."""

    @staticmethod
    def simple_embed(text: str) -> list[float]:
        """Simple embedding for testing (bag of chars)."""
        vec = [0.0] * 26
        for c in text.lower():
            if 'a' <= c <= 'z':
                vec[ord(c) - ord('a')] += 1
        # Normalize
        magnitude = sum(x*x for x in vec) ** 0.5
        if magnitude > 0:
            vec = [x / magnitude for x in vec]
        return vec

    def test_cosine_similarity(self) -> None:
        """Cosine similarity should work correctly."""
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        c = [0.0, 1.0, 0.0]

        assert _cosine_similarity(a, b) == pytest.approx(1.0)
        assert _cosine_similarity(a, c) == pytest.approx(0.0)

    def test_add_and_search(self) -> None:
        """Should find similar entries."""
        memory = SemanticMemory(
            embedding_func=self.simple_embed,
            similarity_threshold=0.3,
        )

        memory.add(MemoryEntry(content="hello world"))
        memory.add(MemoryEntry(content="goodbye world"))
        memory.add(MemoryEntry(content="xyz"))

        results = memory.search("hello there")

        # "hello world" should be most similar
        assert len(results) >= 1
        assert "hello" in results[0].content.lower()

    def test_similarity_threshold(self) -> None:
        """Should filter by threshold."""
        memory = SemanticMemory(
            embedding_func=self.simple_embed,
            similarity_threshold=0.99,  # Very high threshold
        )

        memory.add(MemoryEntry(content="abc"))

        results = memory.search("xyz")

        assert len(results) == 0  # Nothing similar enough

    def test_add_with_embedding(self) -> None:
        """Should accept pre-computed embedding."""
        memory = SemanticMemory(embedding_func=self.simple_embed)
        entry = MemoryEntry(content="test")
        embedding = [1.0, 0.0, 0.0]

        memory.add_with_embedding(entry, embedding)

        assert memory.get_embedding(entry.id) == embedding

    def test_remove(self) -> None:
        """Should remove entry and embedding."""
        memory = SemanticMemory(embedding_func=self.simple_embed)
        entry = MemoryEntry(content="test")

        memory.add(entry)
        assert len(memory) == 1

        removed = memory.remove(entry.id)

        assert removed is True
        assert len(memory) == 0
        assert memory.get_embedding(entry.id) is None


class TestWorkingMemory:
    """Tests for WorkingMemory."""

    def test_set_and_get(self) -> None:
        """Should store and retrieve values."""
        memory = WorkingMemory()

        memory.set("key", "value")

        assert memory.get_value("key") == "value"
        assert memory.has("key") is True

    def test_get_default(self) -> None:
        """Should return default for missing keys."""
        memory = WorkingMemory()

        assert memory.get_value("missing") is None
        assert memory.get_value("missing", "default") == "default"

    def test_ttl_expiration(self) -> None:
        """Should expire items after TTL."""
        memory = WorkingMemory(default_ttl=0.1)  # 100ms

        memory.set("key", "value")
        assert memory.has("key") is True

        time.sleep(0.15)

        assert memory.has("key") is False
        assert memory.get_value("key") is None

    def test_increment(self) -> None:
        """Should increment numeric values."""
        memory = WorkingMemory()

        memory.set("counter", 0)
        result = memory.increment("counter")

        assert result == 1
        assert memory.get_value("counter") == 1

    def test_increment_missing_key(self) -> None:
        """Should raise for missing key."""
        memory = WorkingMemory()

        with pytest.raises(KeyError):
            memory.increment("missing")

    def test_max_items_eviction(self) -> None:
        """Should evict when max items reached."""
        memory = WorkingMemory(max_items=2)

        memory.set("a", 1, priority=0)
        memory.set("b", 2, priority=1)
        memory.set("c", 3, priority=0)  # Should evict "a" (lowest priority, oldest)

        assert memory.has("a") is False
        assert memory.has("b") is True
        assert memory.has("c") is True

    def test_keys_values_items(self) -> None:
        """Should return collections."""
        memory = WorkingMemory()
        memory.set("a", 1)
        memory.set("b", 2)

        assert set(memory.keys()) == {"a", "b"}
        assert set(memory.values()) == {1, 2}
        assert dict(memory.items()) == {"a": 1, "b": 2}

    def test_clear(self) -> None:
        """Should clear all items."""
        memory = WorkingMemory()
        memory.set("key", "value")

        memory.clear()

        assert len(memory) == 0
