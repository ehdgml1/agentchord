"""Example 12: Lifecycle Management with Async Context Managers.

This example demonstrates the new async context manager support for Agent
and Workflow classes, enabling automatic resource cleanup and state persistence.

Key features:
- Automatic memory loading/flushing via context managers
- MCP client cleanup on exit
- Safe resource cleanup even on errors
- Manual cleanup via close() method
"""

from __future__ import annotations

import asyncio
from agentweave.core.agent import Agent
from agentweave.core.workflow import Workflow
from agentweave.memory.conversation import ConversationMemory
from agentweave.memory.stores.sqlite import SQLiteStore


async def example_agent_with_context_manager():
    """Example 1: Agent with async context manager."""
    print("=== Agent Context Manager ===")

    # Create memory store for persistence
    store = SQLiteStore(":memory:")
    memory = ConversationMemory(store=store, namespace="agent_1")

    # Use agent as context manager - resources are automatically cleaned up
    async with Agent(
        name="assistant",
        role="Helpful assistant",
        model="mock-model",
        memory=memory,
    ) as agent:
        result = await agent.run("What is the capital of France?")
        print(f"Response: {result.output}")

        # Memory is automatically saved on exit
        print(f"Memory entries: {len(memory)}")

    # Resources are cleaned up here automatically
    print("Agent cleanup complete\n")


async def example_workflow_with_context_manager():
    """Example 2: Workflow with async context manager."""
    print("=== Workflow Context Manager ===")

    # Create memory stores for each agent
    store1 = SQLiteStore(":memory:")
    store2 = SQLiteStore(":memory:")
    memory1 = ConversationMemory(store=store1, namespace="researcher")
    memory2 = ConversationMemory(store=store2, namespace="writer")

    agents = [
        Agent(
            name="researcher",
            role="Research expert",
            model="mock-model",
            memory=memory1,
        ),
        Agent(
            name="writer",
            role="Content writer",
            model="mock-model",
            memory=memory2,
        ),
    ]

    # Use workflow as context manager - all agents are cleaned up
    async with Workflow(agents=agents, flow="researcher -> writer") as workflow:
        result = await workflow.run("Write about Python programming")
        print(f"Response: {result.output}")
        print(f"Status: {result.status.value}")

    # All agent resources are cleaned up here
    print("Workflow cleanup complete\n")


async def example_manual_cleanup():
    """Example 3: Manual cleanup with close() method."""
    print("=== Manual Cleanup ===")

    store = SQLiteStore(":memory:")
    memory = ConversationMemory(store=store, namespace="agent_2")

    agent = Agent(
        name="assistant",
        role="Helpful assistant",
        model="mock-model",
        memory=memory,
    )

    # Use the agent
    result = await agent.run("Hello!")
    print(f"Response: {result.output}")

    # Manually cleanup resources
    await agent.close()
    print("Manual cleanup complete\n")


async def example_error_handling():
    """Example 4: Cleanup happens even on errors."""
    print("=== Cleanup on Error ===")

    store = SQLiteStore(":memory:")
    memory = ConversationMemory(store=store, namespace="agent_3")

    try:
        async with Agent(
            name="assistant",
            role="Helpful assistant",
            model="mock-model",
            memory=memory,
        ) as agent:
            await agent.run("This might fail")
            # Even if an error occurs, cleanup happens automatically
            print("Operation completed")
    except Exception as e:
        print(f"Error occurred: {e}")

    # Cleanup still happened despite the error
    print("Cleanup completed despite error\n")


async def example_nested_workflows():
    """Example 5: Nested workflows with proper cleanup."""
    print("=== Nested Workflows ===")

    # Create multiple workflows with shared cleanup behavior
    async with Workflow(
        agents=[
            Agent(name="a", role="Agent A", model="mock-model"),
            Agent(name="b", role="Agent B", model="mock-model"),
        ],
        flow="a -> b"
    ) as wf1:
        result1 = await wf1.run("First workflow")
        print(f"Workflow 1 result: {result1.output}")

        # Can nest workflows
        async with Workflow(
            agents=[
                Agent(name="c", role="Agent C", model="mock-model"),
                Agent(name="d", role="Agent D", model="mock-model"),
            ],
            flow="[c, d]"
        ) as wf2:
            result2 = await wf2.run("Second workflow")
            print(f"Workflow 2 result: {result2.output}")

        # wf2 cleaned up here
        print("Inner workflow cleaned up")

    # wf1 cleaned up here
    print("Outer workflow cleaned up\n")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("AgentWeave Lifecycle Management Examples")
    print("="*60 + "\n")

    # Note: These examples use mock providers for demonstration
    # In real usage, you would use actual LLM providers

    print("Note: Using mock providers for demonstration\n")

    await example_agent_with_context_manager()
    await example_workflow_with_context_manager()
    await example_manual_cleanup()
    await example_error_handling()
    await example_nested_workflows()

    print("="*60)
    print("All examples completed!")
    print("="*60)


if __name__ == "__main__":
    # Use mock provider for examples
    import sys
    sys.path.insert(0, "tests")
    from conftest import MockLLMProvider

    # Monkey-patch the registry to use mock provider
    from agentweave.llm.registry import get_registry
    registry = get_registry()
    registry.register("mock", lambda model: MockLLMProvider(model=model), prefixes=["mock"])

    asyncio.run(main())
