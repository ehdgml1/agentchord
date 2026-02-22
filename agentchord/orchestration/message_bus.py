"""Message bus for agent-to-agent communication.

Provides async pub/sub messaging between agents in a team,
with message history tracking and optional callback integration.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

from agentchord.orchestration.types import AgentMessage, MessageType

from agentchord.tracking.callbacks import CallbackEvent

if TYPE_CHECKING:
    from agentchord.tracking.callbacks import CallbackManager


class MessageBus:
    """Async message routing between agents.

    Each registered agent gets a dedicated asyncio.Queue for receiving messages.
    Messages can be sent directly to a specific agent or broadcast to all.

    Example:
        >>> bus = MessageBus()
        >>> bus.register("researcher")
        >>> bus.register("writer")
        >>> await bus.send(AgentMessage(sender="researcher", recipient="writer", ...))
        >>> msg = await bus.receive("writer")
    """

    def __init__(
        self, callbacks: CallbackManager | None = None, max_history: int = 10000
    ) -> None:
        """Initialize message bus.

        Args:
            callbacks: Optional callback manager for message tracking.
            max_history: Maximum number of messages to keep in history (default 10000).
                Set to 0 for unlimited history.
        """
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}
        self._history: deque[AgentMessage] = deque(
            maxlen=max_history if max_history else None
        )
        self._callbacks = callbacks
        self._max_history = max_history

    def register(self, agent_name: str) -> None:
        """Register an agent to receive messages.

        Args:
            agent_name: Name of the agent to register.
        """
        if agent_name not in self._queues:
            self._queues[agent_name] = asyncio.Queue()

    def unregister(self, agent_name: str) -> None:
        """Unregister an agent.

        Args:
            agent_name: Name of the agent to unregister.
        """
        self._queues.pop(agent_name, None)

    @property
    def registered_agents(self) -> list[str]:
        """List of registered agent names."""
        return list(self._queues.keys())

    async def send(self, message: AgentMessage) -> None:
        """Send a message to a specific agent or broadcast.

        Args:
            message: Message to send.
        """
        self._history.append(message)

        if self._callbacks:
            await self._callbacks.emit(
                CallbackEvent.ORCHESTRATION_MESSAGE,
                sender=message.sender,
                recipient=message.recipient,
                message_type=message.message_type.value,
                content=message.content[:200],
            )

        if message.recipient is None or message.message_type == MessageType.BROADCAST:
            # Broadcast to all except sender
            for name, queue in self._queues.items():
                if name != message.sender:
                    await queue.put(message)
        else:
            queue = self._queues.get(message.recipient)
            if queue is not None:
                await queue.put(message)

    async def receive(
        self, agent_name: str, timeout: float | None = None
    ) -> AgentMessage | None:
        """Receive next message for an agent.

        Args:
            agent_name: Name of the agent to receive message for.
            timeout: Timeout in seconds (default 30.0).

        Returns:
            Next message or None if timeout expires or agent not registered.
        """
        queue = self._queues.get(agent_name)
        if queue is None:
            return None

        try:
            if timeout is not None:
                return await asyncio.wait_for(queue.get(), timeout=timeout)
            return await asyncio.wait_for(queue.get(), timeout=30.0)
        except TimeoutError:
            return None

    async def broadcast(
        self, sender: str, content: str, metadata: dict | None = None
    ) -> AgentMessage:
        """Convenience method to broadcast a message to all agents.

        Args:
            sender: Agent sending the broadcast.
            content: Message content.
            metadata: Optional metadata dictionary.

        Returns:
            The broadcast message that was sent.
        """
        message = AgentMessage(
            sender=sender,
            recipient=None,
            message_type=MessageType.BROADCAST,
            content=content,
            metadata=metadata or {},
        )
        await self.send(message)
        return message

    def get_history(self) -> list[AgentMessage]:
        """Return all messages in chronological order."""
        return list(self._history)

    def get_agent_messages(self, agent_name: str) -> list[AgentMessage]:
        """Return messages sent by or to a specific agent.

        Args:
            agent_name: Agent name to filter by.

        Returns:
            List of messages where agent is sender or recipient.
        """
        return [
            m
            for m in self._history
            if m.sender == agent_name or m.recipient == agent_name
        ]

    def clear(self) -> None:
        """Clear all message history and queues."""
        self._history.clear()
        for queue in self._queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    @property
    def message_count(self) -> int:
        """Total number of messages sent."""
        return len(self._history)

    @property
    def max_history(self) -> int:
        """Maximum number of messages to keep in history."""
        return self._max_history

    def pending_count(self, agent_name: str) -> int:
        """Number of unread messages for an agent.

        Args:
            agent_name: Agent name to check.

        Returns:
            Number of pending messages.
        """
        queue = self._queues.get(agent_name)
        return queue.qsize() if queue else 0
