"""A2A (Agent2Agent Protocol) integration.

A2A is an open protocol by Google that enables communication between
AI agents, allowing them to discover and collaborate with each other.

Example:
    >>> from agentchord.protocols.a2a import A2AClient, AgentCard
    >>> client = A2AClient("http://localhost:8080")
    >>> card = await client.get_agent_card()
    >>> print(card.name)
"""

from agentchord.protocols.a2a.types import (
    AgentCard,
    AgentSkill,
    A2ATask,
    A2ATaskStatus,
    A2AMessage,
)

__all__ = [
    "AgentCard",
    "AgentSkill",
    "A2ATask",
    "A2ATaskStatus",
    "A2AMessage",
]


def __getattr__(name: str):
    """Lazy import for client and server."""
    if name == "A2AClient":
        from agentchord.protocols.a2a.client import A2AClient
        return A2AClient
    elif name == "A2AServer":
        from agentchord.protocols.a2a.server import A2AServer
        return A2AServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
