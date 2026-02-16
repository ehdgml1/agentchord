# Memory Guide

AgentWeave provides three complementary memory systems for different use cases: conversation memory for chat history, semantic memory for knowledge retrieval, and working memory for temporary state.

## Quick Start

Store conversation history with minimal setup:

```python
from agentweave import Agent
from agentweave.memory import ConversationMemory

memory = ConversationMemory(max_entries=100)

agent = Agent(
    name="assistant",
    role="Helpful chatbot",
    model="gpt-4o-mini",
    memory=memory
)

# Each conversation turn is automatically saved
result = agent.run_sync("What is the capital of France?")
print(result.output)  # "The capital of France is Paris."

# Subsequent calls can reference previous context
result = agent.run_sync("Tell me about it")
# Agent remembers previous conversation and understands "it" refers to Paris
```

## MemoryEntry

All memory systems work with `MemoryEntry` objects:

```python
from agentweave.memory import MemoryEntry
from datetime import datetime

entry = MemoryEntry(
    content="Python is a programming language",
    role="system",  # "user", "assistant", "system"
    metadata={"source": "documentation", "confidence": 0.95}
)

print(entry.id)         # Auto-generated UUID
print(entry.timestamp)  # Auto-generated current time
print(entry.content)
print(entry.metadata)
```

### Entry Roles

- `user` - Messages from the user
- `assistant` - Responses from the agent
- `system` - System instructions or knowledge

## Conversation Memory

Stores recent conversation history with a sliding window.

### Basic Usage

```python
from agentweave.memory import ConversationMemory, MemoryEntry

memory = ConversationMemory(max_entries=100)

# Add entries
memory.add(MemoryEntry(content="Hello", role="user"))
memory.add(MemoryEntry(content="Hi there!", role="assistant"))
memory.add(MemoryEntry(content="How are you?", role="user"))
memory.add(MemoryEntry(content="I'm doing well, thanks!", role="assistant"))

print(len(memory))  # 4
```

### Retrieving Messages

Get recent conversation history:

```python
# Get most recent 2 messages
recent = memory.get_recent(limit=2)
for entry in recent:
    print(f"{entry.role}: {entry.content}")
# Output:
# user: How are you?
# assistant: I'm doing well, thanks!
```

### Searching History

Simple substring search through conversation:

```python
# Search for messages containing "Python"
results = memory.search("Python", limit=5)
for entry in results:
    print(f"{entry.role}: {entry.content}")
```

Note: Searches from most recent backwards, up to the limit.

### Converting to LLM Format

Get messages in the format needed for LLM APIs:

```python
messages = memory.to_messages()
# Returns: [
#   {"role": "user", "content": "Hello"},
#   {"role": "assistant", "content": "Hi there!"},
#   ...
# ]
```

### Properties

```python
memory = ConversationMemory(max_entries=100)

print(memory.max_entries)  # Maximum entries before oldest is removed
print(len(memory))         # Current number of entries

# Iterate over all entries in chronological order
for entry in memory:
    print(f"{entry.timestamp}: {entry.role} - {entry.content}")
```

### Clearing Memory

```python
memory.clear()
print(len(memory))  # 0
```

## Semantic Memory

Retrieves knowledge based on semantic similarity using embeddings.

### Setup with Embedding Function

```python
from agentweave.memory import SemanticMemory, MemoryEntry

# Provide an embedding function
# This example uses a simple character-based embedding
def simple_embed(text: str) -> list[float]:
    """Simple embedding for demo purposes."""
    vec = [0.0] * 100
    for char in text[:100]:
        vec[ord(char) % 100] += 1.0
    # Normalize
    magnitude = sum(x*x for x in vec) ** 0.5
    if magnitude > 0:
        vec = [x / magnitude for x in vec]
    return vec

memory = SemanticMemory(
    embedding_func=simple_embed,
    similarity_threshold=0.3,
    max_entries=1000
)
```

### Using with Real Embeddings

For production, use a real embedding service:

```python
from agentweave.memory import SemanticMemory
import httpx
import json

async def openai_embed(text: str) -> list[float]:
    """Get embeddings from OpenAI API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            json={"input": text, "model": "text-embedding-3-small"},
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
        )
        data = response.json()
        return data["data"][0]["embedding"]

memory = SemanticMemory(
    embedding_func=openai_embed,
    similarity_threshold=0.5
)
```

### Adding Knowledge

```python
facts = [
    "Python is a high-level programming language",
    "Machine learning uses neural networks",
    "Databases store structured data",
    "APIs enable software communication",
]

for fact in facts:
    memory.add(MemoryEntry(content=fact))

print(len(memory))  # 4
```

### Semantic Search

Find entries by semantic meaning, not just keywords:

```python
# Search for similar content
results = memory.search("coding languages", limit=2)
# May return entries about Python even if exact keywords don't match

for entry in results:
    print(f"Match: {entry.content} (score: {entry.metadata.get('similarity')})")
```

### Properties

```python
print(memory.similarity_threshold)  # Minimum score to include results
print(len(memory))                   # Number of stored entries
```

## Working Memory

Temporary key-value store with TTL (time-to-live) for session state.

### Basic Usage

```python
from agentweave.memory import WorkingMemory

memory = WorkingMemory(
    default_ttl=300,  # 5 minutes default expiration
    max_items=100
)

# Store values
memory.set("user_id", "alice_123")
memory.set("session_step", 1)
memory.set("context", {"task": "analysis", "data": [1, 2, 3]})

# Retrieve values
user_id = memory.get_value("user_id")  # "alice_123"
step = memory.get_value("session_step")  # 1
context = memory.get_value("context")  # {"task": "analysis", "data": [1, 2, 3]}

# Non-existent key returns None
missing = memory.get_value("nonexistent")  # None
```

### Custom TTL

Control when values expire:

```python
# Short-lived: expires in 30 seconds
memory.set("otp_code", "123456", ttl=30)

# Long-lived: expires in 1 hour
memory.set("user_token", "xyz", ttl=3600)

# No expiration (use carefully)
memory.set("permanent", "value", ttl=None)
```

### Priorities

Assign priorities to items:

```python
# High priority items survive longer
memory.set("critical_flag", True, priority=1)
memory.set("debug_info", "...", priority=0)

# When max_items is reached, low-priority items are evicted first
```

### Incrementing Values

Convenient for counters:

```python
memory.set("attempts", 0)
memory.increment("attempts")
memory.increment("attempts", 2)

value = memory.get_value("attempts")  # 3
```

### Iteration

```python
for key, value in memory.items():
    print(f"{key}: {value}")
```

### Properties

```python
print(memory.default_ttl)  # Default expiration time in seconds
print(len(memory))         # Current number of items
print(memory.max_items)    # Maximum items before eviction
```

### Cleanup

```python
memory.clear()
print(len(memory))  # 0
```

## Using Memory with Agents

### Conversation Memory

Agents automatically add messages to attached memory:

```python
from agentweave import Agent
from agentweave.memory import ConversationMemory

memory = ConversationMemory(max_entries=50)

agent = Agent(
    name="assistant",
    role="Helpful chatbot",
    model="gpt-4o-mini",
    memory=memory
)

# Each run adds user input and agent response to memory
agent.run_sync("What is AI?")
agent.run_sync("Tell me more")

# Memory now contains the conversation history
print(len(memory))  # 4 entries (2 user, 2 assistant)

# Recent queries can reference previous context
recent = memory.get_recent(limit=10)
```

### Multi-Turn Conversations

```python
from agentweave import Agent
from agentweave.memory import ConversationMemory

memory = ConversationMemory(max_entries=100)

agent = Agent(
    name="researcher",
    role="Research assistant",
    model="gpt-4o-mini",
    memory=memory
)

# Turn 1
result1 = agent.run_sync("Summarize the history of Python programming")
print(f"Turn 1: {result1.output[:100]}...")

# Turn 2 - agent has context from Turn 1
result2 = agent.run_sync("How has it evolved in the last 5 years?")
print(f"Turn 2: {result2.output[:100]}...")

# Turn 3 - agent can reference both previous turns
result3 = agent.run_sync("What do you think is next?")
print(f"Turn 3: {result3.output[:100]}...")

# Inspect full memory
messages = memory.to_messages()
print(f"Total conversation turns: {len(messages) // 2}")
```

## Memory Persistence

### Saving Memory

```python
import json
from agentweave.memory import ConversationMemory

memory = ConversationMemory()
# ... add entries ...

# Convert to serializable format
messages = memory.to_messages()
with open("conversation.json", "w") as f:
    json.dump(messages, f)
```

### Loading Memory

```python
from agentweave.memory import ConversationMemory, MemoryEntry
import json

memory = ConversationMemory()

with open("conversation.json", "r") as f:
    messages = json.load(f)

# Restore from saved messages
for msg in messages:
    memory.add(MemoryEntry(
        content=msg["content"],
        role=msg["role"]
    ))
```

## Best Practices

### 1. Choose the Right Memory Type

- **ConversationMemory**: Chat applications, multi-turn interactions
- **SemanticMemory**: Knowledge bases, fact retrieval, RAG
- **WorkingMemory**: Session state, counters, temporary context

### 2. Set Appropriate Limits

```python
# For long-running chatbots
memory = ConversationMemory(max_entries=200)  # Keep larger history

# For quick interactions
memory = ConversationMemory(max_entries=20)   # Keep only recent turns
```

### 3. Clean Up Expired Working Memory

```python
memory = WorkingMemory(default_ttl=600, max_items=100)

# Expired items are automatically removed on access
# Periodically check status
if len(memory) > memory.max_items * 0.8:
    print("Working memory getting full, consider cleanup")
```

### 4. Combine Memory Types

```python
from agentweave import Agent
from agentweave.memory import ConversationMemory, WorkingMemory

conv_memory = ConversationMemory(max_entries=50)
work_memory = WorkingMemory(default_ttl=600)

agent = Agent(
    name="assistant",
    role="Assistant",
    model="gpt-4o-mini",
    memory=conv_memory  # Only ConversationMemory attached to agent
)

# Use working memory separately for state
work_memory.set("user_preference", "verbose")
work_memory.set("interaction_count", 0)

# Use semantic memory separately for knowledge
from agentweave.memory import SemanticMemory
knowledge = SemanticMemory(embedding_func=my_embed_func)
```

### 5. Consider Privacy

```python
# Don't store sensitive data in memory
memory.add(MemoryEntry(
    content="User preferences (non-sensitive data)",
    role="system"
))

# For sensitive data, store only references
memory.add(MemoryEntry(
    content="User has stored payment info",
    role="system",
    metadata={"sensitive": True}
))
```

### 6. Memory Size Trade-offs

Larger memory = better context, but slower operations:

```python
# For quality conversations
memory = ConversationMemory(max_entries=500)  # Slower, richer context

# For responsive interactions
memory = ConversationMemory(max_entries=20)   # Faster, limited context
```

## Complete Example

```python
from agentweave import Agent
from agentweave.memory import ConversationMemory, WorkingMemory

async def main():
    # Setup conversation memory
    conv_memory = ConversationMemory(max_entries=100)

    # Setup working memory for session state
    work_memory = WorkingMemory(default_ttl=3600)

    # Create agent with conversation memory
    agent = Agent(
        name="support_bot",
        role="Customer support representative",
        model="gpt-4o-mini",
        memory=conv_memory
    )

    # Track interaction count separately
    work_memory.set("interaction_count", 0)

    # Multi-turn conversation
    queries = [
        "I need help with my account",
        "I forgot my password",
        "Can you reset it for me?"
    ]

    for query in queries:
        # Increment interaction counter
        count = work_memory.get_value("interaction_count") or 0
        work_memory.set("interaction_count", count + 1)

        # Run agent - it automatically uses conversation memory
        result = agent.run_sync(query)
        print(f"Turn {count + 1}: {result.output}\n")

    # Inspect stored conversation
    messages = conv_memory.to_messages()
    print(f"Conversation history: {len(messages)} messages")
    for msg in messages[:3]:
        print(f"  {msg['role']}: {msg['content'][:50]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## See Also

- [Tools Guide](tools.md) - Use memory with tool calling
- [Agent Documentation](../api/core.md) - Agent API details
- [Examples](../examples.md) - Complete memory examples
