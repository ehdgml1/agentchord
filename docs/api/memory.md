# Memory API Reference

Complete API reference for memory systems that enable agents to retain and retrieve context.

## MemoryEntry

A single entry in agent memory.

```python
from agentweave.memory import MemoryEntry
from datetime import datetime

entry = MemoryEntry(
    content="The capital of France is Paris",
    role="assistant",
    metadata={"source": "wikipedia"}
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | UUID | Unique entry identifier |
| `content` | `str` | Required | Entry content/text |
| `role` | `str` | "user" | Role: user, assistant, system |
| `timestamp` | `datetime` | now() | When entry was created |
| `metadata` | `dict[str, Any]` | {} | Additional metadata |

**Example:**

```python
entry = MemoryEntry(
    content="Python is a programming language",
    role="assistant",
    metadata={"category": "programming", "confidence": 0.95}
)
print(entry.id)        # UUID string
print(entry.timestamp) # datetime
```

## BaseMemory

Abstract base class for memory implementations.

```python
from agentweave.memory import BaseMemory, MemoryEntry
from abc import ABC, abstractmethod

class CustomMemory(BaseMemory):
    def add(self, entry: MemoryEntry) -> None:
        # Implementation
        pass

    def get(self, entry_id: str) -> MemoryEntry | None:
        # Implementation
        pass

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        # Implementation
        pass

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        # Implementation
        pass

    def clear(self) -> None:
        # Implementation
        pass

    def __len__(self) -> int:
        # Implementation
        pass
```

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add` | `add(entry: MemoryEntry) -> None` | `None` | Add entry to memory (abstract) |
| `get` | `get(entry_id: str) -> MemoryEntry \| None` | `MemoryEntry \| None` | Get entry by ID (abstract) |
| `get_recent` | `get_recent(limit: int = 10) -> list[MemoryEntry]` | `list[MemoryEntry]` | Get N most recent entries (abstract) |
| `search` | `search(query: str, limit: int = 5) -> list[MemoryEntry]` | `list[MemoryEntry]` | Search entries by query (abstract) |
| `clear` | `clear() -> None` | `None` | Clear all entries (abstract) |
| `__len__` | `__len__() -> int` | `int` | Get number of entries (abstract) |

## ConversationMemory

Stores conversation history between agent and user.

```python
from agentweave.memory import ConversationMemory, MemoryEntry
from agentweave.core import Agent

# Create memory
memory = ConversationMemory(max_entries=1000)

# Create agent with memory
agent = Agent(
    name="assistant",
    role="You are helpful",
    memory=memory
)

# Memory persists across runs
result1 = await agent.run("My name is Alice")
result2 = await agent.run("What is my name?")  # Agent remembers from memory

# Access memory directly
recent = memory.get_recent(limit=5)
for entry in recent:
    print(f"{entry.role}: {entry.content}")

# Search memory
results = memory.search("Python", limit=3)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_entries` | `int` | 1000 | Maximum entries to store |

**Methods:**

Inherits from `BaseMemory`:
- `add(entry: MemoryEntry) -> None` - Add conversation entry
- `get(entry_id: str) -> MemoryEntry | None` - Get entry by ID
- `get_recent(limit: int = 10) -> list[MemoryEntry]` - Get recent entries
- `search(query: str, limit: int = 5) -> list[MemoryEntry]` - Search by content
- `clear() -> None` - Clear all entries
- `__len__() -> int` - Get entry count

**Example:**

```python
memory = ConversationMemory(max_entries=100)

# Add entries
user_msg = MemoryEntry(content="What is AI?", role="user")
assist_msg = MemoryEntry(content="AI is...", role="assistant")

memory.add(user_msg)
memory.add(assist_msg)

# Retrieve
recent = memory.get_recent(limit=10)
assert len(recent) == 2

# Search
results = memory.search("AI", limit=5)
assert len(results) > 0

# Clear
memory.clear()
assert len(memory) == 0
```

## SemanticMemory

Stores entries with semantic similarity search.

```python
from agentweave.memory import SemanticMemory, MemoryEntry

# Create semantic memory
memory = SemanticMemory(
    max_entries=500,
    similarity_threshold=0.5
)

# Add entries
memory.add(MemoryEntry(
    content="Python is a programming language",
    role="assistant"
))

memory.add(MemoryEntry(
    content="JavaScript runs in browsers",
    role="assistant"
))

# Search by semantic similarity
results = memory.search("programming languages", limit=3)
# Returns entries semantically similar to query
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_entries` | `int` | 500 | Maximum entries to store |
| `similarity_threshold` | `float` | 0.5 | Minimum similarity score (0-1) |

**Methods:**

Inherits from `BaseMemory`:
- `add(entry: MemoryEntry) -> None` - Add entry
- `get(entry_id: str) -> MemoryEntry | None` - Get entry by ID
- `get_recent(limit: int = 10) -> list[MemoryEntry]` - Get recent entries
- `search(query: str, limit: int = 5) -> list[MemoryEntry]` - Semantic similarity search
- `clear() -> None` - Clear all entries
- `__len__() -> int` - Get entry count

## WorkingMemory

Key-value store for facts and state during execution.

```python
from agentweave.memory import WorkingMemory
from agentweave.core import Agent

# Create working memory
working_mem = WorkingMemory(default_ttl=3600)

# Create agent
agent = Agent(
    name="processor",
    role="You process data",
    memory=working_mem
)

# Agent can store values
working_mem.set("user_id", "12345")
working_mem.set("processed_count", 0, ttl=300)  # 5 min TTL

# Retrieve values
user_id = working_mem.get("user_id")
count = working_mem.get("processed_count")

# Delete value
working_mem.delete("user_id")

# List keys
keys = working_mem.keys()

# Clear all
working_mem.clear()
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_ttl` | `int \| None` | None | Default TTL in seconds (None = no expiry) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `set` | `set(key: str, value: Any, ttl: int \| None = None) -> None` | `None` | Store key-value pair |
| `get` | `get(key: str) -> Any \| None` | `Any \| None` | Retrieve value by key |
| `delete` | `delete(key: str) -> None` | `None` | Delete key-value pair |
| `keys` | `keys() -> list[str]` | `list[str]` | Get all keys |
| `clear` | `clear() -> None` | `None` | Clear all entries |

**Example:**

```python
memory = WorkingMemory(default_ttl=600)

# Store facts
memory.set("project_name", "AgentWeave")
memory.set("version", "1.0.0")
memory.set("request_count", 0)

# Retrieve
print(memory.get("project_name"))  # "AgentWeave"

# Increment counter
count = memory.get("request_count") or 0
memory.set("request_count", count + 1)

# Keys
print(memory.keys())  # ["project_name", "version", "request_count"]

# Delete
memory.delete("project_name")
print(memory.get("project_name"))  # None
```

## Complete Example: Multi-Memory Agent

```python
from agentweave.memory import ConversationMemory, WorkingMemory
from agentweave.core import Agent

# Create both memory types
conversation = ConversationMemory(max_entries=1000)
working = WorkingMemory(default_ttl=3600)

# Create agent with primary memory
agent = Agent(
    name="researcher",
    role="You are a research assistant",
    memory=conversation
)

# Use working memory for temporary facts
working.set("research_topic", "Machine Learning")
working.set("sources_found", 0)

# Run agent
result = await agent.run("Find information about deep learning")

# Retrieve from conversation memory
recent = conversation.get_recent(limit=5)
print(f"Recent messages: {len(recent)}")

# Search conversation history
ml_results = conversation.search("machine learning", limit=10)
print(f"ML-related entries: {len(ml_results)}")

# Update working memory
sources = working.get("sources_found") or 0
working.set("sources_found", sources + 1)
```

## Memory Best Practices

1. **Choose Right Memory Type**:
   - Use `ConversationMemory` for conversation history
   - Use `SemanticMemory` for semantic search
   - Use `WorkingMemory` for temporary facts

2. **Set Appropriate Limits**:
   ```python
   # Balance memory capacity with performance
   memory = ConversationMemory(max_entries=100)  # Smaller for low-latency
   memory = ConversationMemory(max_entries=10000)  # Larger for long conversations
   ```

3. **Use TTL for Temporary Data**:
   ```python
   working = WorkingMemory(default_ttl=300)  # 5 min expiry
   working.set("temp_token", "abc123", ttl=60)  # 1 min expiry
   ```

4. **Clear Memory When Needed**:
   ```python
   # Start fresh conversation
   memory.clear()
   ```

5. **Search Efficiently**:
   ```python
   # Limit search results
   results = memory.search("Python", limit=5)
   ```

See the [Memory Guide](../guides/memory.md) for more usage examples.
