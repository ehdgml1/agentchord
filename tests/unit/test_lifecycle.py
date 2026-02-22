"""Tests for Agent and Workflow lifecycle management."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agentchord.core.agent import Agent
from agentchord.core.workflow import Workflow
from agentchord.core.types import LLMResponse, Usage
from agentchord.memory.conversation import ConversationMemory
from agentchord.memory.base import MemoryEntry
from tests.conftest import MockLLMProvider


class TestAgentLifecycle:
    """Agent async context manager tests."""

    @pytest.mark.asyncio
    async def test_agent_as_context_manager(self):
        """Agent can be used as async context manager."""
        provider = MockLLMProvider()
        async with Agent(name="test", role="Test", llm_provider=provider) as agent:
            result = await agent.run("Hello")
            assert result.output

    @pytest.mark.asyncio
    async def test_agent_context_manager_returns_self(self):
        """__aenter__ returns the agent itself."""
        provider = MockLLMProvider()
        agent = Agent(name="test", role="Test", llm_provider=provider)
        async with agent as a:
            assert a is agent

    @pytest.mark.asyncio
    async def test_agent_flushes_memory_on_exit(self):
        """Memory is flushed to store on context exit."""
        # Create memory with a mock store
        from agentchord.memory.stores.base import MemoryStore

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.save_many = AsyncMock()
        mock_store.load = AsyncMock(return_value=[])

        memory = ConversationMemory(store=mock_store, namespace="test")
        provider = MockLLMProvider()

        async with Agent(
            name="test", role="Test", llm_provider=provider, memory=memory
        ) as agent:
            await agent.run("Hello")

        # save_to_store should have been called on exit
        mock_store.save_many.assert_called()

    @pytest.mark.asyncio
    async def test_agent_loads_memory_on_enter(self):
        """Memory loads from store on context enter."""
        from agentchord.memory.stores.base import MemoryStore

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.load = AsyncMock(
            return_value=[
                MemoryEntry(content="Previous msg", role="user"),
            ]
        )

        memory = ConversationMemory(store=mock_store, namespace="test")
        provider = MockLLMProvider()

        async with Agent(
            name="test", role="Test", llm_provider=provider, memory=memory
        ) as agent:
            # Memory should have loaded the previous entry
            assert len(memory) == 1

    @pytest.mark.asyncio
    async def test_agent_close_method(self):
        """agent.close() performs cleanup."""
        provider = MockLLMProvider()
        agent = Agent(name="test", role="Test", llm_provider=provider)
        await agent.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_agent_cleanup_on_error(self):
        """Cleanup runs even if agent.run() raises."""
        from agentchord.memory.stores.base import MemoryStore
        from agentchord.errors.exceptions import AgentExecutionError

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.save_many = AsyncMock()
        mock_store.load = AsyncMock(return_value=[])

        memory = ConversationMemory(store=mock_store, namespace="test")

        # Provider that raises
        provider = MockLLMProvider()
        provider.complete = AsyncMock(side_effect=ConnectionError("fail"))

        with pytest.raises(AgentExecutionError):
            async with Agent(
                name="test", role="Test", llm_provider=provider, memory=memory
            ) as agent:
                await agent.run("Hello")

        # Cleanup should still have happened
        # (save_to_store called even though run() failed)
        mock_store.save_many.assert_called()

    @pytest.mark.asyncio
    async def test_agent_no_memory_no_error(self):
        """Agent without memory doesn't error on cleanup."""
        provider = MockLLMProvider()
        async with Agent(name="test", role="Test", llm_provider=provider) as agent:
            await agent.run("Hello")
        # Should not raise

    @pytest.mark.asyncio
    async def test_agent_mcp_disconnect_on_exit(self):
        """MCP client disconnected on context exit."""
        provider = MockLLMProvider()
        mock_mcp = AsyncMock()
        mock_mcp.disconnect_all = AsyncMock()

        async with Agent(
            name="test", role="Test", llm_provider=provider, mcp_client=mock_mcp
        ) as agent:
            pass

        mock_mcp.disconnect_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_cleanup_error_suppressed(self):
        """Cleanup errors don't mask original exception."""
        provider = MockLLMProvider()
        mock_mcp = AsyncMock()
        mock_mcp.disconnect_all = AsyncMock(side_effect=RuntimeError("cleanup fail"))

        # Should not raise RuntimeError from cleanup
        async with Agent(
            name="test", role="Test", llm_provider=provider, mcp_client=mock_mcp
        ) as agent:
            pass

    @pytest.mark.asyncio
    async def test_agent_memory_without_store(self):
        """Agent with memory but no store doesn't error."""
        memory = ConversationMemory()  # No store
        provider = MockLLMProvider()

        async with Agent(
            name="test", role="Test", llm_provider=provider, memory=memory
        ) as agent:
            await agent.run("Hello")
        # Should not raise

    @pytest.mark.asyncio
    async def test_agent_memory_store_save_error_suppressed(self):
        """Memory store save errors don't crash cleanup."""
        from agentchord.memory.stores.base import MemoryStore

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.load = AsyncMock(return_value=[])
        mock_store.save_many = AsyncMock(side_effect=RuntimeError("save failed"))

        memory = ConversationMemory(store=mock_store, namespace="test")
        provider = MockLLMProvider()

        # Should not raise despite save_many error
        async with Agent(
            name="test", role="Test", llm_provider=provider, memory=memory
        ) as agent:
            await agent.run("Hello")

    @pytest.mark.asyncio
    async def test_agent_close_idempotent(self):
        """agent.close() can be called multiple times safely."""
        provider = MockLLMProvider()
        agent = Agent(name="test", role="Test", llm_provider=provider)

        await agent.close()
        await agent.close()  # Second call should not raise

    @pytest.mark.asyncio
    async def test_agent_close_with_memory(self):
        """agent.close() flushes memory."""
        from agentchord.memory.stores.base import MemoryStore

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.save_many = AsyncMock()
        mock_store.load = AsyncMock(return_value=[])

        memory = ConversationMemory(store=mock_store, namespace="test")
        provider = MockLLMProvider()

        agent = Agent(name="test", role="Test", llm_provider=provider, memory=memory)
        await agent.run("Hello")
        await agent.close()

        mock_store.save_many.assert_called()


class TestWorkflowLifecycle:
    """Workflow async context manager tests."""

    @pytest.mark.asyncio
    async def test_workflow_as_context_manager(self):
        """Workflow can be used as async context manager."""
        provider = MockLLMProvider()
        agents = [
            Agent(name="a", role="A", llm_provider=provider),
            Agent(name="b", role="B", llm_provider=provider),
        ]
        async with Workflow(agents=agents, flow="a -> b") as wf:
            result = await wf.run("Hello")
            assert result.is_success

    @pytest.mark.asyncio
    async def test_workflow_context_manager_returns_self(self):
        """__aenter__ returns the workflow itself."""
        provider = MockLLMProvider()
        agents = [Agent(name="a", role="A", llm_provider=provider)]
        wf = Workflow(agents=agents, flow="a")
        async with wf as w:
            assert w is wf

    @pytest.mark.asyncio
    async def test_workflow_cleans_up_all_agents(self):
        """All agents get cleaned up on workflow exit."""
        provider = MockLLMProvider()
        mock_mcp1 = AsyncMock()
        mock_mcp1.disconnect_all = AsyncMock()
        mock_mcp2 = AsyncMock()
        mock_mcp2.disconnect_all = AsyncMock()

        agents = [
            Agent(name="a", role="A", llm_provider=provider, mcp_client=mock_mcp1),
            Agent(name="b", role="B", llm_provider=provider, mcp_client=mock_mcp2),
        ]

        async with Workflow(agents=agents, flow="a -> b") as wf:
            pass

        mock_mcp1.disconnect_all.assert_called_once()
        mock_mcp2.disconnect_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_close_method(self):
        """workflow.close() performs cleanup."""
        provider = MockLLMProvider()
        agents = [Agent(name="a", role="A", llm_provider=provider)]
        wf = Workflow(agents=agents, flow="a")
        await wf.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_workflow_cleanup_continues_on_agent_error(self):
        """If one agent's cleanup fails, others still get cleaned up."""
        provider = MockLLMProvider()
        mock_mcp1 = AsyncMock()
        mock_mcp1.disconnect_all = AsyncMock(side_effect=RuntimeError("fail1"))
        mock_mcp2 = AsyncMock()
        mock_mcp2.disconnect_all = AsyncMock()

        agents = [
            Agent(name="a", role="A", llm_provider=provider, mcp_client=mock_mcp1),
            Agent(name="b", role="B", llm_provider=provider, mcp_client=mock_mcp2),
        ]

        async with Workflow(agents=agents, flow="a -> b") as wf:
            pass

        # Both should have been called, even though first one failed
        mock_mcp1.disconnect_all.assert_called_once()
        mock_mcp2.disconnect_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_with_agent_memory_stores(self):
        """Workflow cleanup saves memory for all agents."""
        from agentchord.memory.stores.base import MemoryStore

        provider = MockLLMProvider()

        mock_store1 = AsyncMock(spec=MemoryStore)
        mock_store1.save_many = AsyncMock()
        mock_store1.load = AsyncMock(return_value=[])

        mock_store2 = AsyncMock(spec=MemoryStore)
        mock_store2.save_many = AsyncMock()
        mock_store2.load = AsyncMock(return_value=[])

        memory1 = ConversationMemory(store=mock_store1, namespace="agent1")
        memory2 = ConversationMemory(store=mock_store2, namespace="agent2")

        agents = [
            Agent(name="a", role="A", llm_provider=provider, memory=memory1),
            Agent(name="b", role="B", llm_provider=provider, memory=memory2),
        ]

        async with Workflow(agents=agents, flow="a -> b") as wf:
            await wf.run("Hello")

        # Both stores should have saved
        mock_store1.save_many.assert_called()
        mock_store2.save_many.assert_called()

    @pytest.mark.asyncio
    async def test_workflow_cleanup_on_execution_error(self):
        """Workflow cleanup happens even if execution fails."""
        from agentchord.memory.stores.base import MemoryStore

        provider = MockLLMProvider()
        provider.complete = AsyncMock(side_effect=RuntimeError("exec fail"))

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.save_many = AsyncMock()
        mock_store.load = AsyncMock(return_value=[])

        memory = ConversationMemory(store=mock_store, namespace="test")
        agents = [Agent(name="a", role="A", llm_provider=provider, memory=memory)]

        async with Workflow(agents=agents, flow="a") as wf:
            result = await wf.run("Hello")
            # Should return failed result instead of raising

        # Cleanup should still happen
        mock_store.save_many.assert_called()

    @pytest.mark.asyncio
    async def test_workflow_close_idempotent(self):
        """workflow.close() can be called multiple times safely."""
        provider = MockLLMProvider()
        agents = [Agent(name="a", role="A", llm_provider=provider)]
        wf = Workflow(agents=agents, flow="a")

        await wf.close()
        await wf.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_workflow_empty_agents_no_crash(self):
        """Empty workflow doesn't crash on cleanup."""
        wf = Workflow(agents=[])
        await wf.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_workflow_agent_load_on_enter(self):
        """Workflow loads agent memory on __aenter__."""
        from agentchord.memory.stores.base import MemoryStore

        provider = MockLLMProvider()

        mock_store = AsyncMock(spec=MemoryStore)
        mock_store.load = AsyncMock(
            return_value=[MemoryEntry(content="Previous", role="user")]
        )

        memory = ConversationMemory(store=mock_store, namespace="test")
        agents = [Agent(name="a", role="A", llm_provider=provider, memory=memory)]

        async with Workflow(agents=agents, flow="a") as wf:
            # Memory should be loaded
            assert len(memory) == 1

    @pytest.mark.asyncio
    async def test_workflow_parallel_agent_cleanup(self):
        """Workflow with parallel agents cleans up all of them."""
        provider = MockLLMProvider()
        mock_mcp1 = AsyncMock()
        mock_mcp1.disconnect_all = AsyncMock()
        mock_mcp2 = AsyncMock()
        mock_mcp2.disconnect_all = AsyncMock()

        agents = [
            Agent(name="a", role="A", llm_provider=provider, mcp_client=mock_mcp1),
            Agent(name="b", role="B", llm_provider=provider, mcp_client=mock_mcp2),
        ]

        async with Workflow(agents=agents, flow="[a, b]") as wf:
            pass

        mock_mcp1.disconnect_all.assert_called_once()
        mock_mcp2.disconnect_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_sequential_agent_cleanup(self):
        """Workflow with sequential agents cleans up all of them."""
        provider = MockLLMProvider()
        mock_mcp1 = AsyncMock()
        mock_mcp1.disconnect_all = AsyncMock()
        mock_mcp2 = AsyncMock()
        mock_mcp2.disconnect_all = AsyncMock()
        mock_mcp3 = AsyncMock()
        mock_mcp3.disconnect_all = AsyncMock()

        agents = [
            Agent(name="a", role="A", llm_provider=provider, mcp_client=mock_mcp1),
            Agent(name="b", role="B", llm_provider=provider, mcp_client=mock_mcp2),
            Agent(name="c", role="C", llm_provider=provider, mcp_client=mock_mcp3),
        ]

        async with Workflow(agents=agents, flow="a -> b -> c") as wf:
            pass

        mock_mcp1.disconnect_all.assert_called_once()
        mock_mcp2.disconnect_all.assert_called_once()
        mock_mcp3.disconnect_all.assert_called_once()
