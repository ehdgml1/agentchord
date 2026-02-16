"""Callback system for observability."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime


class CallbackEvent(str, Enum):
    """Events that can trigger callbacks."""

    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"

    # LLM interactions
    LLM_START = "llm_start"
    LLM_END = "llm_end"
    LLM_ERROR = "llm_error"

    # Tool usage
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # Workflow events
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    WORKFLOW_STEP = "workflow_step"

    # Memory events
    MEMORY_ADD = "memory_add"
    MEMORY_SEARCH = "memory_search"

    # Cost events
    COST_TRACKED = "cost_tracked"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"

    # Orchestration events
    ORCHESTRATION_START = "orchestration_start"
    ORCHESTRATION_END = "orchestration_end"
    ORCHESTRATION_ERROR = "orchestration_error"
    AGENT_DELEGATED = "agent_delegated"
    AGENT_MESSAGE = "agent_message"


@dataclass
class CallbackContext:
    """Context passed to callbacks."""

    event: CallbackEvent
    timestamp: datetime = field(default_factory=datetime.now)
    agent_name: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


# Type aliases
SyncCallback = Callable[[CallbackContext], None]
AsyncCallback = Callable[[CallbackContext], Awaitable[None]]
AnyCallback = SyncCallback | AsyncCallback


class CallbackManager:
    """Manager for event callbacks.

    Supports both sync and async callbacks.
    Callbacks are called in registration order.

    Example:
        >>> manager = CallbackManager()
        >>>
        >>> def on_agent_start(ctx: CallbackContext) -> None:
        ...     print(f"Agent {ctx.agent_name} started")
        >>>
        >>> manager.register(CallbackEvent.AGENT_START, on_agent_start)
        >>> await manager.emit(CallbackEvent.AGENT_START, agent_name="assistant")
    """

    def __init__(self) -> None:
        """Initialize callback manager."""
        self._callbacks: dict[CallbackEvent, list[AnyCallback]] = {}
        self._global_callbacks: list[AnyCallback] = []

    def register(
        self,
        event: CallbackEvent,
        callback: AnyCallback,
    ) -> None:
        """Register a callback for an event.

        Args:
            event: Event to listen for.
            callback: Callback function (sync or async).
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def register_global(self, callback: AnyCallback) -> None:
        """Register a callback for all events.

        Args:
            callback: Callback function (sync or async).
        """
        self._global_callbacks.append(callback)

    def unregister(
        self,
        event: CallbackEvent,
        callback: AnyCallback,
    ) -> bool:
        """Unregister a callback.

        Returns:
            True if callback was found and removed.
        """
        if event in self._callbacks:
            try:
                self._callbacks[event].remove(callback)
                return True
            except ValueError:
                pass
        return False

    def unregister_global(self, callback: AnyCallback) -> bool:
        """Unregister a global callback.

        Returns:
            True if callback was found and removed.
        """
        try:
            self._global_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    async def emit(
        self,
        event: CallbackEvent,
        agent_name: str | None = None,
        **data: Any,
    ) -> None:
        """Emit an event to all registered callbacks.

        Args:
            event: Event to emit.
            agent_name: Optional agent name for context.
            **data: Additional data to include in context.
        """
        context = CallbackContext(
            event=event,
            agent_name=agent_name,
            data=data,
        )

        # Collect all callbacks to run
        callbacks: list[AnyCallback] = []
        callbacks.extend(self._global_callbacks)
        callbacks.extend(self._callbacks.get(event, []))

        # Execute callbacks
        for callback in callbacks:
            await self._execute_callback(callback, context)

    def emit_sync(
        self,
        event: CallbackEvent,
        agent_name: str | None = None,
        **data: Any,
    ) -> None:
        """Emit an event synchronously (only calls sync callbacks).

        Args:
            event: Event to emit.
            agent_name: Optional agent name for context.
            **data: Additional data to include in context.
        """
        context = CallbackContext(
            event=event,
            agent_name=agent_name,
            data=data,
        )

        callbacks: list[AnyCallback] = []
        callbacks.extend(self._global_callbacks)
        callbacks.extend(self._callbacks.get(event, []))

        for callback in callbacks:
            if not asyncio.iscoroutinefunction(callback):
                callback(context)

    async def _execute_callback(
        self,
        callback: AnyCallback,
        context: CallbackContext,
    ) -> None:
        """Execute a single callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(context)
            else:
                callback(context)
        except Exception:
            # Callbacks should not break the main flow
            # In production, you might want to log this
            pass

    def clear(self, event: CallbackEvent | None = None) -> None:
        """Clear callbacks.

        Args:
            event: Specific event to clear, or None to clear all.
        """
        if event is None:
            self._callbacks.clear()
            self._global_callbacks.clear()
        elif event in self._callbacks:
            self._callbacks[event].clear()
