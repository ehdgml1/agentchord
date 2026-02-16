"""Tool factories for multi-agent delegation and shared context access.

This module provides factory functions that create Tool instances which enable
a coordinator agent to delegate tasks to team members and access shared state
during multi-agent orchestration.

Key Functions:
    create_delegation_tools: Create LLM-callable tools for task delegation
    create_context_tools: Create tools for reading/writing shared context

Example:
    >>> from agentweave.orchestration import (
    ...     create_delegation_tools,
    ...     create_context_tools,
    ...     SharedContext,
    ...     TeamMember,
    ...     TeamRole,
    ... )
    >>> from agentweave.core.agent import Agent
    >>>
    >>> # Create agents and member info
    >>> researcher = Agent(name="researcher", role="Research Specialist", model="gpt-4o-mini")
    >>> members = [
    ...     ("researcher", researcher, TeamMember(name="researcher", role=TeamRole.SPECIALIST)),
    ... ]
    >>>
    >>> # Create delegation tools
    >>> delegation_tools = create_delegation_tools(members)
    >>>
    >>> # Create shared context tools
    >>> shared_context = SharedContext()
    >>> context_tools = create_context_tools(shared_context)
    >>>
    >>> # Use tools with coordinator agent
    >>> coordinator = Agent(
    ...     name="coordinator",
    ...     role="Team coordinator",
    ...     tools=delegation_tools + context_tools,
    ... )
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentweave.orchestration.types import (
    AgentMessage,
    MessageType,
    TeamMember,
)
from agentweave.tools.base import Tool, ToolParameter

if TYPE_CHECKING:
    from agentweave.core.agent import Agent
    from agentweave.orchestration.message_bus import MessageBus
    from agentweave.orchestration.shared_context import SharedContext


def create_delegation_tools(
    members: list[tuple[str, Any, TeamMember | None]],
    message_bus: MessageBus | None = None,
    sender_name: str = "coordinator",
    on_result: Any | None = None,
) -> list[Tool]:
    """Create delegation tools for each team member.

    Each tool allows the coordinator to delegate a task to a specific agent.
    The LLM can call these tools to distribute work across the team.

    Args:
        members: List of (name, agent, member_info) tuples.
        message_bus: Optional message bus for recording delegation.
        sender_name: Name of the delegating agent (default "coordinator").
        on_result: Optional async callback ``(agent_name, role, result) -> None``
            invoked after each delegation completes.

    Returns:
        List of Tool instances, one per member.
    """
    tools: list[Tool] = []

    for name, agent, member_info in members:
        role_str = member_info.role.value if member_info else "worker"
        capabilities_str = ""
        if member_info and member_info.capabilities:
            capabilities_str = f" Capabilities: {', '.join(member_info.capabilities)}."

        async def _delegate(
            task_description: str,
            context: str = "",
            _agent: Any = agent,
            _name: str = name,
            _role: str = role_str,
        ) -> str:
            input_text = task_description
            if context:
                input_text = f"{task_description}\n\nAdditional context: {context}"

            if message_bus:
                await message_bus.send(AgentMessage(
                    sender=sender_name,
                    recipient=_name,
                    message_type=MessageType.TASK,
                    content=task_description,
                ))

            result = await _agent.run(input_text)

            if message_bus:
                await message_bus.send(AgentMessage(
                    sender=_name,
                    recipient=sender_name,
                    message_type=MessageType.RESULT,
                    content=result.output,
                ))

            if on_result is not None:
                await on_result(_name, _role, result)

            return result.output

        tool = Tool(
            name=f"delegate_to_{name}",
            description=(
                f"Delegate a task to {name} ({role_str}).{capabilities_str} "
                f"Use this when you need {name}'s expertise."
            ),
            parameters=[
                ToolParameter(
                    name="task_description",
                    type="string",
                    description="Clear description of the task to delegate",
                    required=True,
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description="Additional context or information for the agent",
                    required=False,
                ),
            ],
            func=_delegate,
        )
        tools.append(tool)

    return tools


def create_context_tools(
    shared_context: SharedContext,
    agent_name: str = "unknown",
) -> list[Tool]:
    """Create tools for reading/writing shared context.

    Args:
        shared_context: The SharedContext instance to expose.
        agent_name: Name of the agent using these tools (default "unknown").

    Returns:
        List of Tool instances for context access.
    """
    async def _read_context(key: str) -> str:
        value = await shared_context.get(key)
        if value is None:
            return f"No value found for key '{key}'"
        return str(value)

    async def _write_context(key: str, value: str) -> str:
        await shared_context.set(key, value, agent=agent_name)
        return f"Successfully stored '{key}'"

    async def _list_context_keys() -> str:
        keys = await shared_context.keys()
        if not keys:
            return "Shared context is empty"
        return f"Available keys: {', '.join(keys)}"

    return [
        Tool(
            name="read_shared_context",
            description="Read a value from the team's shared context by key.",
            parameters=[
                ToolParameter(
                    name="key",
                    type="string",
                    description="The key to read from shared context",
                    required=True,
                ),
            ],
            func=_read_context,
        ),
        Tool(
            name="write_shared_context",
            description="Write a value to the team's shared context for other agents to access.",
            parameters=[
                ToolParameter(
                    name="key",
                    type="string",
                    description="The key to store the value under",
                    required=True,
                ),
                ToolParameter(
                    name="value",
                    type="string",
                    description="The value to store",
                    required=True,
                ),
            ],
            func=_write_context,
        ),
        Tool(
            name="list_shared_context",
            description="List all available keys in the team's shared context.",
            parameters=[],
            func=_list_context_keys,
        ),
    ]
