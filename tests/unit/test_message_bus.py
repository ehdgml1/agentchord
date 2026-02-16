"""Unit tests for MessageBus."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from agentweave.orchestration.message_bus import MessageBus
from agentweave.orchestration.types import AgentMessage, MessageType
from agentweave.tracking.callbacks import CallbackManager


class TestMessageBus:
    """Test suite for MessageBus."""

    @pytest.mark.asyncio
    async def test_register_agent(self) -> None:
        """Test registering an agent."""
        bus = MessageBus()
        bus.register("agent-1")

        assert "agent-1" in bus.registered_agents
        assert bus.pending_count("agent-1") == 0

    @pytest.mark.asyncio
    async def test_register_duplicate_no_error(self) -> None:
        """Test that registering same agent twice doesn't cause error."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-1")  # Should not raise

        assert bus.registered_agents == ["agent-1"]

    @pytest.mark.asyncio
    async def test_unregister_agent(self) -> None:
        """Test unregistering an agent."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.unregister("agent-1")

        assert "agent-1" not in bus.registered_agents

    @pytest.mark.asyncio
    async def test_registered_agents_list(self) -> None:
        """Test getting list of registered agents."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")
        bus.register("agent-3")

        agents = bus.registered_agents
        assert len(agents) == 3
        assert "agent-1" in agents
        assert "agent-2" in agents
        assert "agent-3" in agents

    @pytest.mark.asyncio
    async def test_send_direct_message(self) -> None:
        """Test sending a direct message to specific agent."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        message = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Do something",
        )
        await bus.send(message)

        # agent-2 should have the message
        assert bus.pending_count("agent-2") == 1
        # agent-1 should not have received it
        assert bus.pending_count("agent-1") == 0

    @pytest.mark.asyncio
    async def test_receive_message(self) -> None:
        """Test receiving a message."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        message = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Do something",
        )
        await bus.send(message)

        received = await bus.receive("agent-2", timeout=1.0)
        assert received is not None
        assert received.sender == "agent-1"
        assert received.content == "Do something"
        assert bus.pending_count("agent-2") == 0

    @pytest.mark.asyncio
    async def test_receive_timeout_returns_none(self) -> None:
        """Test that receive returns None on timeout."""
        bus = MessageBus()
        bus.register("agent-1")

        received = await bus.receive("agent-1", timeout=0.1)
        assert received is None

    @pytest.mark.asyncio
    async def test_broadcast_to_all_except_sender(self) -> None:
        """Test broadcasting message to all agents except sender."""
        bus = MessageBus()
        bus.register("coordinator")
        bus.register("worker-1")
        bus.register("worker-2")

        message = AgentMessage(
            sender="coordinator",
            recipient=None,
            message_type=MessageType.BROADCAST,
            content="All hands on deck",
        )
        await bus.send(message)

        # coordinator should not receive own broadcast
        assert bus.pending_count("coordinator") == 0
        # workers should receive it
        assert bus.pending_count("worker-1") == 1
        assert bus.pending_count("worker-2") == 1

    @pytest.mark.asyncio
    async def test_broadcast_convenience_method(self) -> None:
        """Test broadcast convenience method."""
        bus = MessageBus()
        bus.register("coordinator")
        bus.register("worker-1")
        bus.register("worker-2")

        message = await bus.broadcast(
            sender="coordinator",
            content="Status update",
            metadata={"priority": "high"},
        )

        assert message.message_type == MessageType.BROADCAST
        assert message.content == "Status update"
        assert message.metadata["priority"] == "high"
        assert bus.pending_count("worker-1") == 1
        assert bus.pending_count("worker-2") == 1

    @pytest.mark.asyncio
    async def test_get_history_chronological(self) -> None:
        """Test getting message history in chronological order."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        msg1 = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task 1",
        )
        msg2 = AgentMessage(
            sender="agent-2",
            recipient="agent-1",
            message_type=MessageType.RESULT,
            content="Result 1",
        )

        await bus.send(msg1)
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await bus.send(msg2)

        history = bus.get_history()
        assert len(history) == 2
        assert history[0].content == "Task 1"
        assert history[1].content == "Result 1"

    @pytest.mark.asyncio
    async def test_get_agent_messages_filter(self) -> None:
        """Test filtering messages by agent."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")
        bus.register("agent-3")

        msg1 = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task",
        )
        msg2 = AgentMessage(
            sender="agent-2",
            recipient="agent-3",
            message_type=MessageType.TASK,
            content="Subtask",
        )
        msg3 = AgentMessage(
            sender="agent-3",
            recipient="agent-1",
            message_type=MessageType.RESULT,
            content="Result",
        )

        await bus.send(msg1)
        await bus.send(msg2)
        await bus.send(msg3)

        # agent-2 should have 2 messages (sent one, received one)
        agent2_messages = bus.get_agent_messages("agent-2")
        assert len(agent2_messages) == 2
        assert any(m.content == "Task" for m in agent2_messages)
        assert any(m.content == "Subtask" for m in agent2_messages)

        # agent-1 should have 2 messages (sent one, received one)
        agent1_messages = bus.get_agent_messages("agent-1")
        assert len(agent1_messages) == 2

    @pytest.mark.asyncio
    async def test_clear_history_and_queues(self) -> None:
        """Test clearing all history and queues."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        message = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task",
        )
        await bus.send(message)

        assert bus.message_count == 1
        assert bus.pending_count("agent-2") == 1

        bus.clear()

        assert bus.message_count == 0
        assert bus.pending_count("agent-2") == 0

    @pytest.mark.asyncio
    async def test_message_count(self) -> None:
        """Test message count property."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        assert bus.message_count == 0

        msg1 = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task 1",
        )
        msg2 = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task 2",
        )

        await bus.send(msg1)
        assert bus.message_count == 1

        await bus.send(msg2)
        assert bus.message_count == 2

    @pytest.mark.asyncio
    async def test_pending_count(self) -> None:
        """Test pending message count for an agent."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        assert bus.pending_count("agent-2") == 0

        msg1 = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task 1",
        )
        msg2 = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task 2",
        )

        await bus.send(msg1)
        assert bus.pending_count("agent-2") == 1

        await bus.send(msg2)
        assert bus.pending_count("agent-2") == 2

        await bus.receive("agent-2", timeout=0.1)
        assert bus.pending_count("agent-2") == 1

    @pytest.mark.asyncio
    async def test_send_to_unregistered_agent_no_error(self) -> None:
        """Test that sending to unregistered agent doesn't raise error."""
        bus = MessageBus()

        message = AgentMessage(
            sender="agent-1",
            recipient="unknown-agent",
            message_type=MessageType.TASK,
            content="Task",
        )
        # Should not raise
        await bus.send(message)

        # Message should still be in history
        assert bus.message_count == 1

    @pytest.mark.asyncio
    async def test_receive_unregistered_agent_returns_none(self) -> None:
        """Test that receiving from unregistered agent returns None."""
        bus = MessageBus()

        received = await bus.receive("unknown-agent", timeout=0.1)
        assert received is None

    @pytest.mark.asyncio
    async def test_callback_integration(self) -> None:
        """Test callback manager integration."""
        callback_manager = CallbackManager()
        callback_called = False
        callback_data = {}

        async def on_message(ctx) -> None:  # type: ignore[no-untyped-def]
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = ctx.data

        # Register callback for orchestration messages
        callback_manager.register("orchestration_message", on_message)  # type: ignore[arg-type]

        bus = MessageBus(callbacks=callback_manager)
        bus.register("agent-1")
        bus.register("agent-2")

        message = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Test task with long content that exceeds 200 characters" * 5,
        )
        await bus.send(message)

        # Give callback time to execute
        await asyncio.sleep(0.01)

        assert callback_called
        assert callback_data["sender"] == "agent-1"
        assert callback_data["recipient"] == "agent-2"
        assert callback_data["message_type"] == "task"
        # Content should be truncated to 200 chars
        assert len(callback_data["content"]) == 200

    @pytest.mark.asyncio
    async def test_broadcast_with_none_recipient(self) -> None:
        """Test that None recipient triggers broadcast behavior."""
        bus = MessageBus()
        bus.register("sender")
        bus.register("receiver-1")
        bus.register("receiver-2")

        message = AgentMessage(
            sender="sender",
            recipient=None,
            message_type=MessageType.QUERY,  # Not BROADCAST type
            content="Question for all",
        )
        await bus.send(message)

        # Should broadcast even with non-BROADCAST message type
        assert bus.pending_count("sender") == 0
        assert bus.pending_count("receiver-1") == 1
        assert bus.pending_count("receiver-2") == 1

    @pytest.mark.asyncio
    async def test_multiple_messages_fifo_order(self) -> None:
        """Test that messages are received in FIFO order."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        messages = [
            AgentMessage(
                sender="agent-1",
                recipient="agent-2",
                message_type=MessageType.TASK,
                content=f"Task {i}",
            )
            for i in range(5)
        ]

        for msg in messages:
            await bus.send(msg)

        received_order = []
        for _ in range(5):
            msg = await bus.receive("agent-2", timeout=0.1)
            if msg:
                received_order.append(msg.content)

        assert received_order == ["Task 0", "Task 1", "Task 2", "Task 3", "Task 4"]

    @pytest.mark.asyncio
    async def test_unregister_clears_pending_messages(self) -> None:
        """Test that unregistering an agent clears its queue."""
        bus = MessageBus()
        bus.register("agent-1")
        bus.register("agent-2")

        message = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK,
            content="Task",
        )
        await bus.send(message)

        assert bus.pending_count("agent-2") == 1
        bus.unregister("agent-2")
        assert bus.pending_count("agent-2") == 0

    @pytest.mark.asyncio
    async def test_default_timeout_is_30_seconds(self) -> None:
        """Test that default timeout is 30 seconds."""
        bus = MessageBus()
        bus.register("agent-1")

        # We'll test this by mocking wait_for
        import asyncio
        from unittest.mock import patch

        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
            result = await bus.receive("agent-1")

            # Verify wait_for was called with 30.0 timeout
            assert mock_wait_for.call_count == 1
            call_args = mock_wait_for.call_args
            assert call_args[1]["timeout"] == 30.0
            assert result is None

    @pytest.mark.asyncio
    async def test_max_history_trims_old_messages(self) -> None:
        """Test that max_history trims old messages when limit is exceeded."""
        bus = MessageBus(max_history=5)
        bus.register("agent-1")
        bus.register("agent-2")

        # Send 10 messages
        for i in range(10):
            message = AgentMessage(
                sender="agent-1",
                recipient="agent-2",
                message_type=MessageType.TASK,
                content=f"Task {i}",
            )
            await bus.send(message)

        # Only the last 5 should be kept
        history = bus.get_history()
        assert len(history) == 5
        assert history[0].content == "Task 5"
        assert history[1].content == "Task 6"
        assert history[2].content == "Task 7"
        assert history[3].content == "Task 8"
        assert history[4].content == "Task 9"

    @pytest.mark.asyncio
    async def test_max_history_default_is_10000(self) -> None:
        """Test that default max_history is 10000."""
        bus = MessageBus()
        assert bus.max_history == 10000

    @pytest.mark.asyncio
    async def test_max_history_zero_means_unlimited(self) -> None:
        """Test that max_history=0 means unlimited history."""
        bus = MessageBus(max_history=0)
        bus.register("agent-1")
        bus.register("agent-2")

        # Send 100 messages
        for i in range(100):
            message = AgentMessage(
                sender="agent-1",
                recipient="agent-2",
                message_type=MessageType.TASK,
                content=f"Task {i}",
            )
            await bus.send(message)

        # All 100 should be kept since max_history=0
        history = bus.get_history()
        assert len(history) == 100
        assert history[0].content == "Task 0"
        assert history[99].content == "Task 99"
