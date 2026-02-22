"""Example: Memory Persistence with Storage Backends.

Demonstrates how to use persistent storage with ConversationMemory
using both JSONFileStore and SQLiteStore backends.
"""

import asyncio
from pathlib import Path
import tempfile

from agentchord.memory import ConversationMemory, MemoryEntry
from agentchord.memory.stores import JSONFileStore, SQLiteStore


async def example_json_store():
    """Example using JSON file storage."""
    print("\n=== JSON File Store Example ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create store
        store = JSONFileStore(tmpdir)

        # Create memory with persistence
        memory = ConversationMemory(
            max_entries=100,
            store=store,
            namespace="agent_session_1"
        )

        # Add some entries
        memory.add(MemoryEntry(content="Hello, how are you?", role="user"))
        memory.add(MemoryEntry(content="I'm doing well, thanks!", role="assistant"))
        memory.add(MemoryEntry(content="What's the weather like?", role="user"))

        # Wait for auto-persist to complete
        await asyncio.sleep(0.1)

        # Explicitly save all entries
        count = await memory.save_to_store()
        print(f"Saved {count} entries to JSON store")

        # Simulate new session - create new memory instance
        memory2 = ConversationMemory(
            max_entries=100,
            store=store,
            namespace="agent_session_1"
        )

        # Load previous conversation
        count = await memory2.load_from_store()
        print(f"Loaded {count} entries from JSON store")

        # Display loaded conversation
        for entry in memory2:
            print(f"  {entry.role}: {entry.content}")


async def example_sqlite_store():
    """Example using SQLite storage."""
    print("\n=== SQLite Store Example ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "memory.db"

        # Create store
        store = SQLiteStore(db_path)

        # Create memory with persistence
        memory = ConversationMemory(
            max_entries=100,
            store=store,
            namespace="agent_session_1"
        )

        # Add some entries
        memory.add(MemoryEntry(
            content="Please summarize this document",
            role="user",
            metadata={"document_id": "doc_123"}
        ))
        memory.add(MemoryEntry(
            content="Here's a summary: ...",
            role="assistant",
            metadata={"tokens_used": 150}
        ))

        # Save to store
        await memory.save_to_store()
        print(f"Saved {len(memory)} entries to SQLite store")

        # Close the store properly
        await store.close()

        # Simulate new session with new store instance
        store2 = SQLiteStore(db_path)
        memory2 = ConversationMemory(
            max_entries=100,
            store=store2,
            namespace="agent_session_1"
        )

        # Load previous conversation
        count = await memory2.load_from_store()
        print(f"Loaded {count} entries from SQLite store")

        # Display loaded conversation with metadata
        for entry in memory2:
            meta_str = f" (metadata: {entry.metadata})" if entry.metadata else ""
            print(f"  {entry.role}: {entry.content}{meta_str}")

        await store2.close()


async def example_multiple_namespaces():
    """Example using multiple namespaces with one store."""
    print("\n=== Multiple Namespaces Example ===\n")

    # Use in-memory SQLite for demo
    store = SQLiteStore(":memory:")

    # Create memories for different users
    user1_memory = ConversationMemory(store=store, namespace="user_alice")
    user2_memory = ConversationMemory(store=store, namespace="user_bob")

    # Add entries for each user
    user1_memory.add(MemoryEntry(content="Hi, I'm Alice", role="user"))
    user2_memory.add(MemoryEntry(content="Hello, I'm Bob", role="user"))

    # Wait for auto-persist, then save both explicitly
    await asyncio.sleep(0.1)
    await user1_memory.save_to_store()
    await user2_memory.save_to_store()

    # Load in new memory instances (simulating separate sessions)
    alice_new = ConversationMemory(store=store, namespace="user_alice")
    bob_new = ConversationMemory(store=store, namespace="user_bob")

    await alice_new.load_from_store()
    await bob_new.load_from_store()

    print(f"Alice's conversation ({len(alice_new)} entries):")
    for entry in alice_new:
        print(f"  {entry.content}")

    print(f"\nBob's conversation ({len(bob_new)} entries):")
    for entry in bob_new:
        print(f"  {entry.content}")

    await store.close()


async def example_sliding_window_with_persistence():
    """Example showing how max_entries works with persistence."""
    print("\n=== Sliding Window with Persistence ===\n")

    store = SQLiteStore(":memory:")

    # Create memory with small window
    memory = ConversationMemory(
        max_entries=3,  # Only keep 3 most recent
        store=store,
        namespace="limited_session"
    )

    # Add 5 entries
    for i in range(1, 6):
        memory.add(MemoryEntry(content=f"Message {i}", role="user"))

    # Wait for auto-persist, then save explicitly
    await asyncio.sleep(0.1)
    await memory.save_to_store()
    print(f"In-memory entries: {len(memory)}")
    print(f"  Content: {[e.content for e in memory]}")

    # Load in new memory with same max_entries
    memory2 = ConversationMemory(
        max_entries=3,
        store=store,
        namespace="limited_session"
    )

    count = await memory2.load_from_store()
    print(f"\nTotal entries in store: {count}")
    print(f"Loaded into memory (max 3): {len(memory2)}")
    print(f"  Content: {[e.content for e in memory2]}")

    await store.close()


async def main():
    """Run all examples."""
    await example_json_store()
    await example_sqlite_store()
    await example_multiple_namespaces()
    await example_sliding_window_with_persistence()

    # Give any remaining background tasks time to complete
    await asyncio.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(main())
