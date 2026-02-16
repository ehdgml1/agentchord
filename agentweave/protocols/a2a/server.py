"""A2A Server implementation.

This module provides a server that exposes an Agent via the A2A protocol.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from agentweave.protocols.a2a.types import (
    AgentCard,
    A2ATask,
    A2ATaskStatus,
)

if TYPE_CHECKING:
    from agentweave.core.agent import Agent


class A2AServer:
    """HTTP server that exposes an Agent via A2A protocol.

    A2AServer wraps an Agent and provides HTTP endpoints for:
    - GET /agent-card: Get agent metadata
    - POST /tasks: Create a new task
    - GET /tasks/{id}: Get task status
    - POST /tasks/{id}/cancel: Cancel a task

    Example:
        >>> from agentweave import Agent
        >>> from agentweave.protocols.a2a import A2AServer, AgentCard
        >>>
        >>> agent = Agent(name="assistant", role="Helper")
        >>> card = AgentCard(name="assistant", description="A helpful assistant")
        >>> server = A2AServer(agent, card)
        >>> await server.start(port=8080)

    Note:
        Requires starlette and uvicorn: pip install starlette uvicorn
    """

    def __init__(
        self,
        agent: "Agent",
        card: AgentCard,
    ) -> None:
        """Initialize A2A server.

        Args:
            agent: Agent to expose via A2A.
            card: Agent card (metadata) to advertise.
        """
        self.agent = agent
        self.card = card
        self._tasks: dict[str, A2ATask] = {}
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}
        self._app: Any = None
        self._server: Any = None

    def _create_app(self) -> Any:
        """Create the Starlette application."""
        try:
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse
            from starlette.routing import Route
        except ImportError as e:
            raise ImportError(
                "Starlette not installed. "
                "Install with: pip install starlette uvicorn"
            ) from e

        async def get_agent_card(request: Any) -> JSONResponse:
            """GET /agent-card - Return agent metadata."""
            return JSONResponse(self.card.model_dump())

        async def create_task(request: Any) -> JSONResponse:
            """POST /tasks - Create a new task."""
            try:
                body = await request.json()
            except json.JSONDecodeError:
                return JSONResponse(
                    {"error": "Invalid JSON"},
                    status_code=400,
                )

            input_text = body.get("input")
            if not input_text:
                return JSONResponse(
                    {"error": "Missing 'input' field"},
                    status_code=400,
                )

            task = A2ATask(
                input=input_text,
                metadata=body.get("metadata", {}),
            )
            self._tasks[task.id] = task

            # Start processing in background
            asyncio_task = asyncio.create_task(self._process_task(task.id))
            self._running_tasks[task.id] = asyncio_task

            return JSONResponse(task.model_dump(), status_code=201)

        async def get_task(request: Any) -> JSONResponse:
            """GET /tasks/{task_id} - Get task status."""
            task_id = request.path_params["task_id"]
            task = self._tasks.get(task_id)

            if not task:
                return JSONResponse(
                    {"error": f"Task '{task_id}' not found"},
                    status_code=404,
                )

            return JSONResponse(task.model_dump())

        async def cancel_task(request: Any) -> JSONResponse:
            """POST /tasks/{task_id}/cancel - Cancel a task."""
            task_id = request.path_params["task_id"]
            task = self._tasks.get(task_id)

            if not task:
                return JSONResponse(
                    {"error": f"Task '{task_id}' not found"},
                    status_code=404,
                )

            if task.is_terminal:
                return JSONResponse(
                    {"error": "Task already completed"},
                    status_code=400,
                )

            # Cancel the running task
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]

            task = task.model_copy(
                update={"status": A2ATaskStatus.CANCELLED}
            )
            self._tasks[task_id] = task

            return JSONResponse(task.model_dump())

        async def health_check(request: Any) -> JSONResponse:
            """GET /health - Health check endpoint."""
            return JSONResponse({"status": "healthy"})

        routes = [
            Route("/agent-card", get_agent_card, methods=["GET"]),
            Route("/tasks", create_task, methods=["POST"]),
            Route("/tasks/{task_id}", get_task, methods=["GET"]),
            Route("/tasks/{task_id}/cancel", cancel_task, methods=["POST"]),
            Route("/health", health_check, methods=["GET"]),
        ]

        return Starlette(routes=routes)

    async def _process_task(self, task_id: str) -> None:
        """Process a task in the background."""
        task = self._tasks.get(task_id)
        if not task:
            return

        # Mark as running
        task = task.mark_running()
        self._tasks[task_id] = task

        try:
            # Execute the agent
            result = await self.agent.run(task.input)
            task = task.mark_completed(result.output)
        except asyncio.CancelledError:
            task = task.model_copy(
                update={"status": A2ATaskStatus.CANCELLED}
            )
        except Exception as e:
            task = task.mark_failed(str(e))

        self._tasks[task_id] = task

        # Cleanup
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

    async def start(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        """Start the A2A server.

        Args:
            host: Host to bind to.
            port: Port to listen on.

        Note:
            This method blocks until the server is stopped.
        """
        try:
            import uvicorn
        except ImportError as e:
            raise ImportError(
                "Uvicorn not installed. "
                "Install with: pip install uvicorn"
            ) from e

        self._app = self._create_app()
        self.card = self.card.model_copy(
            update={"url": f"http://{host}:{port}"}
        )

        config = uvicorn.Config(
            self._app,
            host=host,
            port=port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self) -> None:
        """Stop the A2A server."""
        # Cancel all running tasks
        for task_id, asyncio_task in list(self._running_tasks.items()):
            asyncio_task.cancel()

        if self._server:
            self._server.should_exit = True

    def get_task(self, task_id: str) -> A2ATask | None:
        """Get a task by ID.

        Args:
            task_id: Task ID to look up.

        Returns:
            A2ATask if found, None otherwise.
        """
        return self._tasks.get(task_id)

    @property
    def tasks(self) -> dict[str, A2ATask]:
        """Get all tasks."""
        return self._tasks.copy()

    @property
    def app(self) -> Any:
        """Get the Starlette application (for testing or custom deployment)."""
        if self._app is None:
            self._app = self._create_app()
        return self._app

    def __repr__(self) -> str:
        return f"A2AServer(agent={self.agent.name!r}, card={self.card.name!r})"
