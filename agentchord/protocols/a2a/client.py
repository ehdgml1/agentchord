"""A2A Client implementation.

This module provides a client for interacting with A2A agents.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from agentchord.protocols.a2a.types import (
    AgentCard,
    A2ATask,
    A2ATaskStatus,
)


class A2AClientError(Exception):
    """Base exception for A2A client errors."""

    pass


class A2AConnectionError(A2AClientError):
    """Failed to connect to A2A agent."""

    pass


class A2ATaskError(A2AClientError):
    """Error while processing A2A task."""

    pass


class A2AClient:
    """Client for interacting with A2A agents.

    A2AClient provides methods to discover agent capabilities and
    send tasks to remote A2A-compatible agents.

    Example:
        >>> client = A2AClient("http://localhost:8080")
        >>> card = await client.get_agent_card()
        >>> print(f"Connected to: {card.name}")
        >>> task = await client.create_task("Summarize this document")
        >>> result = await client.wait_for_task(task.id)
        >>> print(result.output)
    """

    DEFAULT_TIMEOUT = 30.0
    POLL_INTERVAL = 1.0

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize A2A client.

        Args:
            base_url: Base URL of the A2A agent (e.g., 'http://localhost:8080').
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )
        self._agent_card: AgentCard | None = None

    async def __aenter__(self) -> A2AClient:
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context and close client."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_agent_card(self, force_refresh: bool = False) -> AgentCard:
        """Get the agent's card (metadata).

        Args:
            force_refresh: If True, fetch fresh card from server.

        Returns:
            AgentCard with agent metadata.

        Raises:
            A2AConnectionError: If unable to connect to agent.
        """
        if self._agent_card and not force_refresh:
            return self._agent_card

        try:
            response = await self._client.get("/agent-card")
            response.raise_for_status()
            data = response.json()
            self._agent_card = AgentCard(**data)
            return self._agent_card
        except httpx.ConnectError as e:
            raise A2AConnectionError(
                f"Failed to connect to agent at {self.base_url}: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise A2AConnectionError(
                f"Agent returned error: {e.response.status_code}"
            ) from e

    async def create_task(
        self,
        input: str,
        metadata: dict[str, Any] | None = None,
    ) -> A2ATask:
        """Create a new task for the agent.

        Args:
            input: Task input/prompt.
            metadata: Optional metadata to attach to the task.

        Returns:
            Created A2ATask with assigned ID.

        Raises:
            A2ATaskError: If task creation fails.
        """
        payload = {
            "input": input,
            "metadata": metadata or {},
        }

        try:
            response = await self._client.post("/tasks", json=payload)
            response.raise_for_status()
            data = response.json()
            return A2ATask(**data)
        except httpx.HTTPStatusError as e:
            raise A2ATaskError(
                f"Failed to create task: {e.response.status_code}"
            ) from e

    async def get_task(self, task_id: str) -> A2ATask:
        """Get task status and result.

        Args:
            task_id: Task ID to query.

        Returns:
            A2ATask with current status.

        Raises:
            A2ATaskError: If task query fails.
        """
        try:
            response = await self._client.get(f"/tasks/{task_id}")
            response.raise_for_status()
            data = response.json()
            return A2ATask(**data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise A2ATaskError(f"Task '{task_id}' not found") from e
            raise A2ATaskError(
                f"Failed to get task: {e.response.status_code}"
            ) from e

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float | None = None,
        poll_interval: float = POLL_INTERVAL,
    ) -> A2ATask:
        """Wait for a task to complete.

        Polls the task status until it reaches a terminal state.

        Args:
            task_id: Task ID to wait for.
            timeout: Maximum time to wait in seconds. None means no timeout.
            poll_interval: Time between status checks in seconds.

        Returns:
            A2ATask in terminal state (completed, failed, or cancelled).

        Raises:
            TimeoutError: If timeout is reached before task completes.
            A2ATaskError: If task query fails.
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            task = await self.get_task(task_id)

            if task.is_terminal:
                return task

            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"Task '{task_id}' did not complete within {timeout}s"
                    )

            await asyncio.sleep(poll_interval)

    async def ask(
        self,
        input: str,
        timeout: float | None = None,
    ) -> str:
        """Send a message and wait for response.

        Convenience method that creates a task and waits for completion.

        Args:
            input: Message to send to the agent.
            timeout: Maximum time to wait for response.

        Returns:
            Agent's response as a string.

        Raises:
            A2ATaskError: If task fails.
            TimeoutError: If timeout is reached.
        """
        task = await self.create_task(input)
        task = await self.wait_for_task(task.id, timeout=timeout)

        if task.status == A2ATaskStatus.FAILED:
            raise A2ATaskError(f"Task failed: {task.error}")

        return task.output or ""

    async def cancel_task(self, task_id: str) -> A2ATask:
        """Cancel a running task.

        Args:
            task_id: Task ID to cancel.

        Returns:
            Updated A2ATask.

        Raises:
            A2ATaskError: If cancellation fails.
        """
        try:
            response = await self._client.post(f"/tasks/{task_id}/cancel")
            response.raise_for_status()
            data = response.json()
            return A2ATask(**data)
        except httpx.HTTPStatusError as e:
            raise A2ATaskError(
                f"Failed to cancel task: {e.response.status_code}"
            ) from e

    @property
    def agent_card(self) -> AgentCard | None:
        """Get cached agent card (None if not fetched yet)."""
        return self._agent_card

    def __repr__(self) -> str:
        name = self._agent_card.name if self._agent_card else "unknown"
        return f"A2AClient(url={self.base_url!r}, agent={name!r})"
