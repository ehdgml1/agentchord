"""Execution service layer.

Provides business logic for execution operations:
- Start, stop, resume executions
- Background dispatch (shared by workflows and playground)
- Retrieve execution logs
- Coordinate between API and executor
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.executor import (
    ExecutionStateStore,
    ExecutionStatus,
    NodeExecution,
    Workflow,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutor,
    WorkflowNode,
)
from ..db.database import get_session_factory
from ..models.execution import Execution
from ..repositories.execution_repo import ExecutionRepository


class IExecutionRepository(Protocol):
    """Execution repository interface."""

    async def create(self, execution: Execution) -> Execution:
        """Create execution."""
        ...

    async def get_by_id(self, execution_id: str) -> Execution | None:
        """Get execution by ID."""
        ...

    async def update(self, execution: Execution) -> Execution:
        """Update execution."""
        ...

    async def list_by_workflow(self, workflow_id: str) -> list[Execution]:
        """List executions by workflow."""
        ...


class IWorkflowRepository(Protocol):
    """Workflow repository interface."""

    async def get_by_id(self, workflow_id: str) -> Workflow | None:
        """Get workflow by ID."""
        ...


class ExecutionNotFoundError(Exception):
    """Execution not found."""

    def __init__(self, execution_id: str) -> None:
        super().__init__(f"Execution '{execution_id}' not found")
        self.execution_id = execution_id


class ExecutionNotResumableError(Exception):
    """Execution cannot be resumed."""

    def __init__(self, execution_id: str, status: str) -> None:
        super().__init__(f"Execution '{execution_id}' with status '{status}' cannot be resumed")
        self.execution_id = execution_id
        self.status = status


class ExecutionNotStoppableError(Exception):
    """Execution cannot be stopped."""

    def __init__(self, execution_id: str, status: str) -> None:
        super().__init__(f"Execution '{execution_id}' with status '{status}' cannot be stopped")
        self.execution_id = execution_id
        self.status = status


class ExecutionService:
    """Service layer for execution operations.

    Provides:
        - Start new executions
        - Stop running executions
        - Resume failed/paused executions
        - Retrieve execution logs
    """

    STOPPABLE_STATUSES = {
        ExecutionStatus.RUNNING.value,
        ExecutionStatus.PAUSED.value,
        ExecutionStatus.RETRYING.value,
    }

    RESUMABLE_STATUSES = {
        ExecutionStatus.FAILED.value,
        ExecutionStatus.PAUSED.value,
        ExecutionStatus.TIMED_OUT.value,
    }

    def __init__(
        self,
        executor: WorkflowExecutor,
        execution_repo: IExecutionRepository,
        workflow_repo: IWorkflowRepository,
        state_store: ExecutionStateStore,
    ) -> None:
        """Initialize service.

        Args:
            executor: Workflow executor.
            execution_repo: Execution repository.
            workflow_repo: Workflow repository.
            state_store: Execution state store.
        """
        self.executor = executor
        self.execution_repo = execution_repo
        self.workflow_repo = workflow_repo
        self.state_store = state_store

    @staticmethod
    def build_executor_workflow(model: Any) -> Workflow:
        """Convert DB workflow model to executor Workflow dataclass.

        Extracts nodes/edges JSON from the DB model and constructs the
        executor-compatible Workflow dataclass used by WorkflowExecutor.

        Args:
            model: SQLAlchemy WorkflowModel instance with nodes/edges JSON.

        Returns:
            Executor Workflow dataclass ready for execution.
        """
        nodes_data = json.loads(model.nodes) if isinstance(model.nodes, str) else model.nodes
        edges_data = json.loads(model.edges) if isinstance(model.edges, str) else model.edges

        return Workflow(
            id=model.id,
            name=model.name,
            nodes=[
                WorkflowNode(
                    id=n["id"],
                    type=n["type"],
                    data=n.get("data", {}),
                    position=n.get("position"),
                )
                for n in (nodes_data or [])
            ],
            edges=[
                WorkflowEdge(
                    id=e["id"],
                    source=e["source"],
                    target=e["target"],
                    source_handle=e.get("sourceHandle"),
                    target_handle=e.get("targetHandle"),
                )
                for e in (edges_data or [])
            ],
        )

    async def create_and_dispatch(
        self,
        session: AsyncSession,
        bg_executor: Any,
        workflow_model: Any,
        input_text: str,
        mode: str,
        trigger_type: str = "manual",
        context: dict | None = None,
        user_id: str | None = None,
    ) -> str:
        """Create execution record and dispatch to background executor.

        This is the shared execution dispatch logic used by both the
        workflows API and the playground API. It:
        1. Builds the executor workflow from the DB model.
        2. Creates an initial ExecutionModel record (status='running').
        3. Builds an async closure that runs the executor and updates results.
        4. Dispatches the closure to the background executor.

        Args:
            session: Active database session for creating the execution record.
            bg_executor: BackgroundExecutionManager for async dispatch.
            workflow_model: SQLAlchemy WorkflowModel instance.
            input_text: User input text for execution.
            mode: Execution mode ('full', 'mock', 'debug').
            trigger_type: How execution was triggered ('manual', 'playground', etc.).
            context: Optional execution context (e.g. chat history).
            user_id: Optional user ID for DB key fallback.

        Returns:
            The generated execution_id string.
        """
        executor_workflow = self.build_executor_workflow(workflow_model)

        # Inject user_id for DB key fallback in executor
        exec_context = context.copy() if context else {"input": input_text}
        exec_context["_user_id"] = user_id

        # Create initial execution record
        execution_id = str(uuid.uuid4())

        # Inject SSE execution_id so executor can emit per-node events
        exec_context["_execution_id"] = execution_id
        exec_repo = ExecutionRepository(session)

        now = datetime.now(UTC).replace(tzinfo=None)
        exec_model = Execution(
            id=execution_id,
            workflow_id=workflow_model.id,
            status="running",
            mode=mode,
            trigger_type=trigger_type,
            input=input_text,
            started_at=now,
        )
        await exec_repo.create(exec_model)
        await session.commit()

        # Capture references for the closure
        executor = self.executor

        async def _execute() -> dict[str, Any] | None:
            session_factory = get_session_factory()
            async with session_factory() as bg_session:
                bg_exec_repo = ExecutionRepository(bg_session)
                try:
                    execution = await executor.run(
                        workflow=executor_workflow,
                        input=input_text,
                        mode=mode,
                        context=exec_context,
                        event_emitter=bg_executor,
                    )
                    # Update execution record with results
                    exec_record = await bg_exec_repo.get_by_id(execution_id)
                    if exec_record:
                        exec_record.status = execution.status.value
                        exec_record.output = json.dumps(execution.output) if execution.output else None
                        exec_record.error = execution.error
                        exec_record.completed_at = (
                            execution.completed_at.replace(tzinfo=None)
                            if execution.completed_at
                            else None
                        )
                        if execution.completed_at and exec_record.started_at:
                            exec_record.duration_ms = int(
                                (execution.completed_at - execution.started_at).total_seconds() * 1000
                            )

                        # Token usage
                        token_usage = executor._aggregate_token_usage(execution.context)
                        exec_record.total_tokens = token_usage.get("total_tokens")
                        exec_record.prompt_tokens = token_usage.get("prompt_tokens")
                        exec_record.completion_tokens = token_usage.get("completion_tokens")
                        exec_record.estimated_cost = token_usage.get("estimated_cost")
                        exec_record.model_used = token_usage.get("model_used")

                        # Node logs
                        node_logs = []
                        for ne in execution.node_executions:
                            node_logs.append({
                                "node_id": ne.node_id,
                                "status": ne.status.value if hasattr(ne.status, "value") else ne.status,
                                "input": ne.input,
                                "output": ne.output,
                                "error": ne.error,
                                "started_at": ne.started_at.isoformat() if ne.started_at else None,
                                "completed_at": ne.completed_at.isoformat() if ne.completed_at else None,
                                "duration_ms": ne.duration_ms,
                                "retry_count": ne.retry_count,
                            })
                        exec_record.node_logs = json.dumps(node_logs)

                        await bg_exec_repo.update(exec_record)
                        await bg_session.commit()

                        return {"output": execution.output if execution.output else ""}
                except Exception as e:
                    # Update execution record with error
                    exec_record = await bg_exec_repo.get_by_id(execution_id)
                    if exec_record:
                        exec_record.status = "failed"
                        exec_record.error = str(e)
                        exec_record.completed_at = datetime.now(UTC).replace(tzinfo=None)
                        if exec_record.started_at:
                            exec_record.duration_ms = int(
                                (datetime.now(UTC).replace(tzinfo=None) - exec_record.started_at).total_seconds() * 1000
                            )
                        await bg_exec_repo.update(exec_record)
                        await bg_session.commit()
                    # Re-raise so BackgroundExecutionManager emits "failed" SSE event
                    raise

        # Dispatch to background
        await bg_executor.dispatch(_execute, execution_id)

        return execution_id

    async def start_execution(
        self,
        workflow_id: str,
        input: str,
        mode: str = "full",
        trigger_type: str = "manual",
        trigger_id: str | None = None,
    ) -> Execution:
        """Start a new workflow execution.

        Args:
            workflow_id: ID of workflow to execute.
            input: Workflow input string.
            mode: Execution mode ("full", "mock", "debug").
            trigger_type: How execution was triggered.
            trigger_id: ID of schedule/webhook that triggered.

        Returns:
            Created execution record.

        Raises:
            ValueError: If workflow not found.
        """
        workflow = await self.workflow_repo.get_by_id(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        # Execute workflow
        result = await self.executor.run(
            workflow=workflow,
            input=input,
            mode=mode,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
        )

        # Create execution record
        execution = self._create_execution_record(result)
        await self.execution_repo.create(execution)

        return execution

    async def stop_execution(self, execution_id: str) -> Execution:
        """Stop a running execution.

        Args:
            execution_id: ID of execution to stop.

        Returns:
            Updated execution record.

        Raises:
            ExecutionNotFoundError: If execution not found.
            ExecutionNotStoppableError: If execution cannot be stopped.
        """
        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution:
            raise ExecutionNotFoundError(execution_id)

        if execution.status not in self.STOPPABLE_STATUSES:
            raise ExecutionNotStoppableError(execution_id, execution.status)

        # Stop the executor
        self.executor.stop(execution_id)

        # Update execution record
        execution.status = ExecutionStatus.CANCELLED.value
        execution.completed_at = datetime.now(UTC).replace(tzinfo=None)
        if execution.started_at:
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

        await self.execution_repo.update(execution)
        return execution

    async def resume_execution(self, execution_id: str) -> Execution:
        """Resume a failed or paused execution.

        Args:
            execution_id: ID of execution to resume.

        Returns:
            Updated execution record.

        Raises:
            ExecutionNotFoundError: If execution not found.
            ExecutionNotResumableError: If execution cannot be resumed.
            ValueError: If no saved state or workflow not found.
        """
        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution:
            raise ExecutionNotFoundError(execution_id)

        if execution.status not in self.RESUMABLE_STATUSES:
            raise ExecutionNotResumableError(execution_id, execution.status)

        # Load saved state
        state = await self.state_store.load_state(execution_id)
        if not state:
            raise ValueError(f"No saved state for execution '{execution_id}'")

        # Get workflow
        workflow = await self.workflow_repo.get_by_id(execution.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{execution.workflow_id}' not found")

        # Resume execution
        result = await self.executor.run(
            workflow=workflow,
            input=state["context"].get("input", ""),
            mode=execution.mode,
            trigger_type=execution.trigger_type,
            trigger_id=execution.trigger_id,
            start_from_node=state["current_node"],
            context=state["context"],
        )

        # Update execution record
        self._update_execution_from_result(execution, result)
        await self.execution_repo.update(execution)

        return execution

    async def get_execution_logs(
        self,
        execution_id: str,
        node_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get execution logs.

        Args:
            execution_id: ID of execution.
            node_id: Optional filter by node ID.

        Returns:
            List of node execution logs.

        Raises:
            ExecutionNotFoundError: If execution not found.
        """
        execution = await self.execution_repo.get_by_id(execution_id)
        if not execution:
            raise ExecutionNotFoundError(execution_id)

        # Parse node logs from JSON
        logs = json.loads(execution.node_logs or "[]")

        # Filter by node_id if provided
        if node_id:
            logs = [log for log in logs if log.get("node_id") == node_id]

        return logs

    def _create_execution_record(self, result: WorkflowExecution) -> Execution:
        """Create execution record from result.

        Args:
            result: Workflow execution result.

        Returns:
            Execution entity.
        """
        duration_ms = None
        if result.completed_at and result.started_at:
            duration_ms = int(
                (result.completed_at - result.started_at).total_seconds() * 1000
            )

        # Aggregate token usage from context
        token_usage = self.executor._aggregate_token_usage(result.context)

        return Execution(
            id=result.id,
            workflow_id=result.workflow_id,
            status=result.status.value,
            mode=result.mode,
            trigger_type=result.trigger_type,
            trigger_id=result.trigger_id,
            input=result.input,
            output=json.dumps(result.output) if result.output else None,
            error=result.error,
            node_logs=self._serialize_node_logs(result.node_executions),
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_ms=duration_ms,
            total_tokens=token_usage.get("total_tokens"),
            prompt_tokens=token_usage.get("prompt_tokens"),
            completion_tokens=token_usage.get("completion_tokens"),
            estimated_cost=token_usage.get("estimated_cost"),
            model_used=token_usage.get("model_used"),
        )

    def _update_execution_from_result(
        self,
        execution: Execution,
        result: WorkflowExecution,
    ) -> None:
        """Update execution record from result.

        Args:
            execution: Existing execution record.
            result: New execution result.
        """
        execution.status = result.status.value
        execution.output = json.dumps(result.output) if result.output else None
        execution.error = result.error
        execution.completed_at = result.completed_at

        if result.completed_at and execution.started_at:
            execution.duration_ms = int(
                (result.completed_at - execution.started_at).total_seconds() * 1000
            )

        # Aggregate token usage from context
        token_usage = self.executor._aggregate_token_usage(result.context)
        if token_usage:
            execution.total_tokens = token_usage.get("total_tokens")
            execution.prompt_tokens = token_usage.get("prompt_tokens")
            execution.completion_tokens = token_usage.get("completion_tokens")
            execution.estimated_cost = token_usage.get("estimated_cost")
            execution.model_used = token_usage.get("model_used")

        # Merge node logs
        existing_logs = json.loads(execution.node_logs or "[]")
        new_logs = [self._serialize_node_execution(ne) for ne in result.node_executions]
        execution.node_logs = json.dumps(existing_logs + new_logs)

    def _serialize_node_logs(self, node_executions: list[NodeExecution]) -> str:
        """Serialize node executions to JSON.

        Args:
            node_executions: List of node executions.

        Returns:
            JSON string.
        """
        logs = [self._serialize_node_execution(ne) for ne in node_executions]
        return json.dumps(logs)

    def _serialize_node_execution(self, ne: NodeExecution) -> dict[str, Any]:
        """Serialize single node execution.

        Args:
            ne: Node execution.

        Returns:
            Dictionary representation.
        """
        return {
            "node_id": ne.node_id,
            "status": ne.status.value if isinstance(ne.status, ExecutionStatus) else ne.status,
            "input": ne.input,
            "output": ne.output,
            "error": ne.error,
            "started_at": ne.started_at.isoformat() if ne.started_at else None,
            "completed_at": ne.completed_at.isoformat() if ne.completed_at else None,
            "duration_ms": ne.duration_ms,
            "retry_count": ne.retry_count,
        }
