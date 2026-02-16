"""Workflow execution engine with resilience patterns.

Phase -1 아키텍처 스파이크:
- ExecutionStatus 확장 (PAUSED, QUEUED, RETRYING, TIMED_OUT)
- CircuitBreaker, TimeoutManager, RetryPolicy 통합
- 노드 실행 전 체크포인트 저장
- 워크플로우 검증

Phase 4 확장:
- Parallel execution engine (4.4)
- Safe condition branching with simpleeval (4.5)
- Feedback loop support (4.6)
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
import logging
import re
from typing import Any
import uuid

logger = logging.getLogger(__name__)

# AgentWeave resilience imports
import sys
from pathlib import Path
# Add agentweave package to path (parent of visual-builder)
_agentweave_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _agentweave_root not in sys.path:
    sys.path.insert(0, _agentweave_root)
from agentweave.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from agentweave.resilience.timeout import TimeoutManager
from agentweave.resilience.retry import RetryPolicy, RetryStrategy

from .mcp_manager import MCPManager
from .secret_store import SecretStore


def generate_id() -> str:
    """Generate unique ID."""
    return str(uuid.uuid4())


class _HashEmbeddingProvider:
    """Hash-based embedding fallback when no real provider configured.

    Uses SHA-256 hash to generate deterministic 32-dimensional vectors.
    This is NOT semantic - identical text produces identical vectors,
    but similar text produces different vectors. Suitable only for
    exact-match fallback when no real embedding API is available.
    """

    @property
    def model_name(self) -> str:
        return "hash-embedding"

    @property
    def dimensions(self) -> int:
        return 32

    async def embed(self, text: str) -> list[float]:
        """Generate hash-based embedding vector."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # SHA-256 produces 32 bytes, normalize to [0, 1]
        return [float(b) / 255.0 for b in h]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate hash-based embeddings for batch of texts."""
        return [await self.embed(t) for t in texts]


class ExecutionStatus(str, Enum):
    """확장된 워크플로우 실행 상태.

    Phase -1에서 추가된 상태:
    - QUEUED: 분산 실행 대기 (Celery)
    - PAUSED: 디버그 모드 중단점
    - RETRYING: 재시도 중
    - TIMED_OUT: 타임아웃 (FAILED와 구분)
    """
    PENDING = "pending"
    QUEUED = "queued"          # NEW: 분산 실행 대기
    RUNNING = "running"
    PAUSED = "paused"          # NEW: 디버그 모드 중단점
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"      # NEW: 재시도 중
    TIMED_OUT = "timed_out"    # NEW: 타임아웃


@dataclass
class WorkflowNode:
    """워크플로우 노드."""
    id: str
    type: str  # "agent", "mcp_tool", "condition", "parallel", "feedback_loop"
    data: dict[str, Any]
    position: dict[str, float] | None = None


@dataclass
class WorkflowEdge:
    """워크플로우 엣지 (노드 연결)."""
    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None


@dataclass
class Workflow:
    """워크플로우 정의."""
    id: str
    name: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))


@dataclass
class NodeExecution:
    """개별 노드 실행 결과."""
    node_id: str
    status: ExecutionStatus
    input: Any
    output: Any | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    completed_at: datetime | None = None
    duration_ms: int | None = None
    retry_count: int = 0


@dataclass
class WorkflowExecution:
    """워크플로우 전체 실행 결과."""
    id: str
    workflow_id: str
    status: ExecutionStatus
    mode: str  # "full", "mock", "debug"
    trigger_type: str  # "manual", "cron", "webhook"
    trigger_id: str | None = None
    node_executions: list[NodeExecution] = field(default_factory=list)
    input: str = ""
    output: Any | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    completed_at: datetime | None = None
    context: dict[str, Any] = field(default_factory=dict)


class WorkflowValidationError(Exception):
    """Workflow validation failed."""
    pass


class ExecutionStateStore:
    """실행 상태 저장소 (체크포인트)."""

    def __init__(self, db) -> None:
        self.db = db

    async def save_state(
        self,
        execution_id: str,
        current_node: str,
        context: dict[str, Any],
    ) -> None:
        """현재 실행 상태 저장 (체크포인트)."""
        import json
        await self.db.execute(
            """INSERT INTO execution_states
               (execution_id, current_node, context, updated_at)
               VALUES (:execution_id, :current_node, :context, CURRENT_TIMESTAMP)
               ON CONFLICT(execution_id) DO UPDATE SET
               current_node = excluded.current_node,
               context = excluded.context,
               updated_at = excluded.updated_at""",
            {"execution_id": execution_id, "current_node": current_node, "context": json.dumps(context)},
        )

    async def load_state(self, execution_id: str) -> dict[str, Any] | None:
        """저장된 실행 상태 로드."""
        import json
        row = await self.db.fetchone(
            "SELECT current_node, context FROM execution_states WHERE execution_id = :execution_id",
            {"execution_id": execution_id},
        )
        if row:
            return {
                "current_node": row["current_node"],
                "context": json.loads(row["context"]),
            }
        return None

    async def mark_failed(
        self,
        execution_id: str,
        node_id: str,
        error: str,
    ) -> None:
        """노드 실패 기록."""
        await self.db.execute(
            """UPDATE execution_states
               SET status = 'failed', error = :error, updated_at = CURRENT_TIMESTAMP
               WHERE execution_id = :execution_id""",
            {"error": error, "execution_id": execution_id},
        )

    async def delete_state(self, execution_id: str) -> None:
        """실행 상태 삭제."""
        await self.db.execute(
            "DELETE FROM execution_states WHERE execution_id = :execution_id",
            {"execution_id": execution_id},
        )


class WorkflowExecutor:
    """회복탄력성이 통합된 워크플로우 실행 엔진.

    Features:
        - Circuit breaker per MCP server
        - Timeout management
        - Retry policy for transient failures
        - Checkpoint before each node execution
        - Workflow validation
        - Parallel branch execution (Phase 4.4)
        - Safe condition branching with simpleeval (Phase 4.5)
        - Feedback loop support (Phase 4.6)

    Example:
        >>> executor = WorkflowExecutor(mcp_manager, secret_store, state_store)
        >>> execution = await executor.run(workflow, "input text")
    """

    # Timeout settings
    DEFAULT_NODE_TIMEOUT = 60.0  # Agent
    DEFAULT_TOOL_TIMEOUT = 30.0  # MCP Tool
    DEFAULT_WORKFLOW_TIMEOUT = 300.0  # 5 minutes

    # Retry settings
    MAX_NODE_RETRIES = 3

    # Context size limit
    MAX_CONTEXT_ENTRIES = 500

    VALID_MODES = {"full", "mock", "debug"}

    # Template engine pattern
    TEMPLATE_PATTERN = re.compile(r'\{\{(\w+(?:\.\w+)*)\}\}')

    def __init__(
        self,
        mcp_manager: MCPManager,
        secret_store: SecretStore,
        state_store: ExecutionStateStore,
    ) -> None:
        """Initialize executor.

        Args:
            mcp_manager: MCP server manager.
            secret_store: Secret storage.
            state_store: Execution state storage (checkpoints).
        """
        self.mcp_manager = mcp_manager
        self.secret_store = secret_store
        self.state_store = state_store

        # Resilience components
        self._timeout_manager = TimeoutManager(
            default_timeout=self.DEFAULT_NODE_TIMEOUT,
        )
        self._retry_policy = RetryPolicy(
            max_retries=self.MAX_NODE_RETRIES,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=30.0,
        )

        # Running executions
        self._running: dict[str, asyncio.Task] = {}

        # Cancelled executions
        self._cancelled: set[str] = set()

    async def run(
        self,
        workflow: Workflow,
        input: str,
        mode: str = "full",
        trigger_type: str = "manual",
        trigger_id: str | None = None,
        start_from_node: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Execute workflow.

        Args:
            workflow: Workflow definition.
            input: Workflow input string.
            mode: Execution mode ("full", "mock", "debug").
            trigger_type: How execution was triggered.
            trigger_id: ID of schedule/webhook that triggered.
            start_from_node: Resume from this node (for recovery).
            context: Existing context (for recovery).

        Returns:
            Execution result.

        Raises:
            WorkflowValidationError: If workflow is invalid.
        """
        # Validate workflow
        self._validate_workflow(workflow)

        # Validate mode parameter
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {self.VALID_MODES}")

        # Create execution record
        execution = WorkflowExecution(
            id=generate_id(),
            workflow_id=workflow.id,
            status=ExecutionStatus.RUNNING,
            mode=mode,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            input=input,
        )

        ctx: dict[str, Any] = context or {"input": input}

        try:
            # Get execution order
            ordered_nodes = self._topological_sort(workflow)

            # Build adjacency map for parallel/condition routing
            adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
            for edge in workflow.edges:
                if edge.source in adjacency:
                    adjacency[edge.source].append(edge.target)
            node_map = {n.id: n for n in workflow.nodes}

            # Find start position
            start_index = 0
            if start_from_node:
                for i, node in enumerate(ordered_nodes):
                    if node.id == start_from_node:
                        start_index = i
                        break

            # Track already-executed node IDs (for parallel branch skipping)
            executed_ids: set[str] = set()

            # Track skip_nodes for condition routing (local to this run)
            skip_nodes: set[str] = set()

            # Execute nodes
            for node in ordered_nodes[start_index:]:
                # Check if execution was cancelled
                if execution.id in self._cancelled:
                    execution.status = ExecutionStatus.CANCELLED
                    break

                # Skip nodes already executed by parallel branches
                if node.id in executed_ids:
                    continue

                # Skip nodes deactivated by condition routing
                if node.id in skip_nodes:
                    continue

                # Save checkpoint BEFORE execution
                await self.state_store.save_state(execution.id, node.id, ctx)

                # --- Parallel node handling ---
                if node.type == "parallel":
                    # Execute the parallel node itself first
                    node_result = await self._execute_node_with_retry(
                        execution.id, node, ctx, mode
                    )
                    execution.node_executions.append(node_result)
                    ctx[node.id] = node_result.output

                    # Find downstream branch start nodes
                    branch_starts = []
                    for target_id in adjacency.get(node.id, []):
                        if target_id in node_map:
                            branch_starts.append(node_map[target_id])

                    if branch_starts:
                        parallel_results = await self._execute_parallel_branches(
                            execution.id, node, branch_starts, workflow, ctx, mode
                        )
                        execution.node_executions.extend(parallel_results)

                        # Merge branch outputs into context
                        for result in parallel_results:
                            if result.status == ExecutionStatus.COMPLETED:
                                ctx[result.node_id] = result.output

                        # Check for failures
                        failed = [
                            r for r in parallel_results
                            if r.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT)
                        ]
                        if failed:
                            # Check for error fallback on parallel node
                            error_target = self._find_error_edge_target(node.id, workflow)
                            if error_target and error_target in node_map:
                                ctx[node.id] = {
                                    "error": failed[0].error,
                                    "status": "failed",
                                    "failed_branches": [r.node_id for r in failed],
                                }
                                for edge in workflow.edges:
                                    if edge.source == node.id and edge.source_handle != "error":
                                        skip_nodes.add(edge.target)
                            else:
                                execution.status = ExecutionStatus.FAILED
                                execution.error = f"Parallel branch failed: {failed[0].error}"
                                break

                        # Mark branch nodes as already executed
                        executed_ids.update(r.node_id for r in parallel_results)

                    continue

                # Execute node normally
                node_result = await self._execute_node_with_retry(
                    execution.id, node, ctx, mode
                )
                execution.node_executions.append(node_result)

                if node_result.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
                    # Check for error fallback edges
                    error_target = self._find_error_edge_target(node.id, workflow)
                    if error_target and error_target in node_map:
                        # Route to error handler node with error context
                        ctx[node.id] = {
                            "error": node_result.error,
                            "status": node_result.status.value,
                            "node_id": node.id,
                        }
                        # Skip nodes that are on the normal path from this node
                        for edge in workflow.edges:
                            if edge.source == node.id and edge.source_handle != "error":
                                skip_nodes.add(edge.target)
                        # Continue execution - the error target node will be reached
                        # in the normal topological order
                        continue

                    # No error edge - fail as before
                    if node_result.status == ExecutionStatus.TIMED_OUT:
                        execution.status = ExecutionStatus.TIMED_OUT
                        execution.error = f"Node {node.id} timed out"
                    else:
                        execution.status = ExecutionStatus.FAILED
                        execution.error = node_result.error
                    break

                # Pass result to next node
                ctx[node.id] = node_result.output

                # Warn if context grows too large (M2 fix)
                if len(ctx) > self.MAX_CONTEXT_ENTRIES:
                    logger.warning(
                        f"Execution context has {len(ctx)} entries, exceeding {self.MAX_CONTEXT_ENTRIES} limit. "
                        "Consider splitting into smaller workflows."
                    )

                # --- Condition routing ---
                if node.type == "condition" and node_result.status == ExecutionStatus.COMPLETED:
                    condition_output = node_result.output
                    active_handle = (
                        condition_output.get("active_handle", "true")
                        if isinstance(condition_output, dict)
                        else "true"
                    )

                    # Track which paths are active based on edge sourceHandles
                    for edge in workflow.edges:
                        if edge.source == node.id:
                            if edge.source_handle and edge.source_handle != active_handle:
                                # This edge leads to an inactive branch
                                skip_nodes.add(edge.target)

                # --- Feedback loop iteration ---
                if node.type == "feedback_loop" and node_result.status == ExecutionStatus.COMPLETED:
                    output = node_result.output
                    if isinstance(output, dict) and output.get("continue_loop"):
                        loop_body_id = node.data.get("loopBodyStart")
                        if loop_body_id:
                            # Find the loop body nodes between loopBodyStart and this feedback node
                            loop_body_nodes = self._get_loop_body_nodes(
                                loop_body_id, node.id, ordered_nodes, adjacency
                            )
                            if loop_body_nodes:
                                # Execute loop body in a controlled while loop
                                loop_failed = await self._execute_feedback_loop_body(
                                    execution, node, loop_body_nodes,
                                    workflow, ctx, mode, ordered_nodes, adjacency
                                )
                                if loop_failed:
                                    break

            # Mark completed if no failures
            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.COMPLETED
                # Get final output from last node
                if execution.node_executions:
                    execution.output = execution.node_executions[-1].output

            # Store context for token usage aggregation
            execution.context = ctx

            # Clean up checkpoint on success
            if execution.status == ExecutionStatus.COMPLETED:
                await self.state_store.delete_state(execution.id)

        except asyncio.CancelledError:
            execution.status = ExecutionStatus.CANCELLED
            execution.context = ctx
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            execution.context = ctx

        execution.completed_at = datetime.now(UTC).replace(tzinfo=None)

        # Clean up cancellation tracking (M5 fix)
        self._cancelled.discard(execution.id)

        return execution

    async def _execute_parallel_branches(
        self,
        execution_id: str,
        parallel_node: WorkflowNode,
        branch_start_nodes: list[WorkflowNode],
        workflow: Workflow,
        context: dict[str, Any],
        mode: str,
    ) -> list[NodeExecution]:
        """Execute parallel branches concurrently.

        Args:
            execution_id: Parent execution ID.
            parallel_node: The parallel gateway node.
            branch_start_nodes: First node of each branch.
            workflow: Workflow definition.
            context: Shared execution context (each branch gets a copy).
            mode: Execution mode.

        Returns:
            List of node execution results from all branches.
        """

        async def run_branch(start_node: WorkflowNode) -> list[NodeExecution]:
            """Run a single branch starting from given node."""
            branch_results = []
            branch_ctx = dict(context)  # Copy context for branch

            # Build adjacency for finding next nodes
            adj: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
            for edge in workflow.edges:
                if edge.source in adj:
                    adj[edge.source].append(edge.target)
            node_map_local = {n.id: n for n in workflow.nodes}

            # Walk the branch chain
            current = start_node
            visited: set[str] = set()
            while current and current.id not in visited:
                visited.add(current.id)

                await self.state_store.save_state(execution_id, current.id, branch_ctx)
                node_result = await self._execute_node_with_retry(
                    execution_id, current, branch_ctx, mode
                )
                branch_results.append(node_result)

                if node_result.status != ExecutionStatus.COMPLETED:
                    break

                branch_ctx[current.id] = node_result.output

                # Find next node in this branch (first downstream that isn't a merge point)
                next_nodes = adj.get(current.id, [])
                if len(next_nodes) == 1:
                    next_id = next_nodes[0]
                    # Stop if this node has multiple incoming edges (merge point)
                    incoming = sum(1 for e in workflow.edges if e.target == next_id)
                    if incoming > 1:
                        break  # Merge point - stop this branch
                    current = node_map_local.get(next_id)
                else:
                    break  # End of branch or fork

            return branch_results

        # Run all branches concurrently
        branch_tasks = [run_branch(node) for node in branch_start_nodes]
        all_branch_results = await asyncio.gather(*branch_tasks, return_exceptions=True)

        # Flatten results
        results: list[NodeExecution] = []
        for branch_result in all_branch_results:
            if isinstance(branch_result, Exception):
                results.append(NodeExecution(
                    node_id="unknown",
                    status=ExecutionStatus.FAILED,
                    input=None,
                    error=str(branch_result),
                ))
            else:
                results.extend(branch_result)

        return results

    def _get_loop_body_nodes(
        self,
        loop_body_start_id: str,
        feedback_node_id: str,
        ordered_nodes: list[WorkflowNode],
        adjacency: dict[str, list[str]],
    ) -> list[WorkflowNode]:
        """Get nodes that form the loop body between start and feedback node.

        Args:
            loop_body_start_id: ID of the first node in the loop body.
            feedback_node_id: ID of the feedback_loop node.
            ordered_nodes: Topologically sorted nodes.
            adjacency: Adjacency map.

        Returns:
            Ordered list of nodes in the loop body.
        """
        # Collect nodes between loop_body_start and feedback_node in topo order
        body_nodes = []
        in_body = False
        for node in ordered_nodes:
            if node.id == loop_body_start_id:
                in_body = True
            if in_body and node.id != feedback_node_id:
                body_nodes.append(node)
            if node.id == feedback_node_id:
                break
        return body_nodes

    # Hard safety cap for feedback loops
    HARD_MAX_LOOP_ITERATIONS = 1000

    async def _execute_feedback_loop_body(
        self,
        execution: WorkflowExecution,
        feedback_node: WorkflowNode,
        loop_body_nodes: list[WorkflowNode],
        workflow: Workflow,
        ctx: dict[str, Any],
        mode: str,
        ordered_nodes: list[WorkflowNode],
        adjacency: dict[str, list[str]],
    ) -> bool:
        """Execute feedback loop body repeatedly until exit condition.

        Args:
            execution: The workflow execution record.
            feedback_node: The feedback_loop node.
            loop_body_nodes: Nodes in the loop body.
            workflow: Workflow definition.
            ctx: Execution context (mutated in place).
            mode: Execution mode.
            ordered_nodes: Topologically sorted nodes.
            adjacency: Adjacency map.

        Returns:
            True if the loop ended due to failure, False otherwise.
        """
        iteration_counter = 0
        while True:
            # Hard safety cap to prevent infinite loops
            iteration_counter += 1
            if iteration_counter > self.HARD_MAX_LOOP_ITERATIONS:
                execution.status = ExecutionStatus.FAILED
                execution.error = f"Feedback loop exceeded hard limit of {self.HARD_MAX_LOOP_ITERATIONS} iterations"
                return True
            # Re-execute loop body nodes
            for body_node in loop_body_nodes:
                await self.state_store.save_state(execution.id, body_node.id, ctx)

                body_result = await self._execute_node_with_retry(
                    execution.id, body_node, ctx, mode
                )
                execution.node_executions.append(body_result)

                if body_result.status == ExecutionStatus.FAILED:
                    execution.status = ExecutionStatus.FAILED
                    execution.error = body_result.error
                    return True
                elif body_result.status == ExecutionStatus.TIMED_OUT:
                    execution.status = ExecutionStatus.TIMED_OUT
                    execution.error = f"Node {body_node.id} timed out"
                    return True

                ctx[body_node.id] = body_result.output

            # Re-execute the feedback loop node to check exit condition
            await self.state_store.save_state(execution.id, feedback_node.id, ctx)
            loop_result = await self._execute_node_with_retry(
                execution.id, feedback_node, ctx, mode
            )
            execution.node_executions.append(loop_result)

            if loop_result.status != ExecutionStatus.COMPLETED:
                execution.status = ExecutionStatus.FAILED
                execution.error = loop_result.error or "Feedback loop node failed"
                return True

            ctx[feedback_node.id] = loop_result.output

            loop_output = loop_result.output
            if not isinstance(loop_output, dict) or not loop_output.get("continue_loop"):
                # Exit the loop
                break

        return False

    async def _execute_node_with_retry(
        self,
        execution_id: str,
        node: WorkflowNode,
        context: dict[str, Any],
        mode: str,
    ) -> NodeExecution:
        """Execute node with retry logic.

        Args:
            execution_id: Parent execution ID.
            node: Node to execute.
            context: Execution context.
            mode: Execution mode.

        Returns:
            Node execution result.
        """
        started_at = datetime.now(UTC).replace(tzinfo=None)
        retry_count = 0
        last_error: str | None = None

        for attempt in range(self.MAX_NODE_RETRIES + 1):
            try:
                # Get appropriate timeout
                timeout = self._get_node_timeout(node)

                # Execute with timeout
                output = await asyncio.wait_for(
                    self._execute_node(node, context, mode),
                    timeout=timeout,
                )

                completed_at = datetime.now(UTC).replace(tzinfo=None)
                duration_ms = int((completed_at - started_at).total_seconds() * 1000)

                return NodeExecution(
                    node_id=node.id,
                    status=ExecutionStatus.COMPLETED,
                    input=context.get("input"),
                    output=output,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                )

            except asyncio.TimeoutError:
                return NodeExecution(
                    node_id=node.id,
                    status=ExecutionStatus.TIMED_OUT,
                    input=context.get("input"),
                    error=f"Timed out after {self._get_node_timeout(node)}s",
                    started_at=started_at,
                    completed_at=datetime.now(UTC).replace(tzinfo=None),
                )

            except CircuitOpenError as e:
                # Don't retry if circuit is open
                return NodeExecution(
                    node_id=node.id,
                    status=ExecutionStatus.FAILED,
                    input=context.get("input"),
                    error=f"Circuit breaker open: {e}",
                    started_at=started_at,
                    completed_at=datetime.now(UTC).replace(tzinfo=None),
                )

            except Exception as e:
                last_error = str(e)
                retry_count += 1

                # Check if should retry
                if not self._retry_policy.should_retry(e, attempt):
                    break

                # Wait before retry
                if attempt < self.MAX_NODE_RETRIES:
                    delay = self._retry_policy.get_delay(attempt)
                    await asyncio.sleep(delay)

        # All retries exhausted
        return NodeExecution(
            node_id=node.id,
            status=ExecutionStatus.FAILED,
            input=context.get("input"),
            error=last_error or "Unknown error",
            started_at=started_at,
            completed_at=datetime.now(UTC).replace(tzinfo=None),
            retry_count=retry_count,
        )

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
        mode: str,
    ) -> Any:
        """Execute single node.

        Args:
            node: Node to execute.
            context: Execution context.
            mode: Execution mode.

        Returns:
            Node output.
        """
        if mode == "mock":
            return self._get_mock_output(node)

        if node.type == "agent":
            return await self._run_agent(node, context)
        elif node.type == "mcp_tool":
            return await self._run_mcp_tool(node, context)
        elif node.type == "condition":
            return await self._run_condition(node, context)
        elif node.type == "parallel":
            return {"parallel": True, "message": "Parallel node - branches executed separately"}
        elif node.type == "feedback_loop":
            return await self._run_feedback_loop(node, context, mode)
        elif node.type == "rag":
            return await self._run_rag(node, context)
        elif node.type == "multi_agent":
            return await self._run_multi_agent(node, context)
        else:
            return None

    async def _run_agent(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> str:
        """Execute agent node using real LLM provider."""
        from agentweave import Agent
        from agentweave.llm.base import BaseLLMProvider
        from app.config import get_settings

        settings = get_settings()
        data = node.data

        # Build MCP tools list if specified
        tools = await self._build_agent_tools(data.get("mcpTools", []))

        # Determine model and create provider with API key from config
        model = data.get("model", settings.default_llm_model)
        provider = self._create_llm_provider(model, settings)

        agent = Agent(
            name=data.get("name", "Agent"),
            role=data.get("role", "AI Assistant"),
            model=model,
            temperature=data.get("temperature", settings.llm_temperature),
            max_tokens=data.get("maxTokens", settings.llm_max_tokens),
            timeout=settings.llm_timeout,
            system_prompt=data.get("systemPrompt"),
            tools=tools or None,
            llm_provider=provider,
        )

        # Get input from previous node or workflow input
        input_text = self._resolve_input(node, context)
        result = await agent.run(input_text)

        # Store usage info in context for tracking
        if result.usage:
            context[f"_usage_{node.id}"] = {
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
                "cost": result.cost,
                "model": model,
            }

        return result.output

    async def _run_rag(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a RAG retrieval+generation node.

        Node data fields:
            documents: list[str] - Document contents to index
            searchLimit: int - Number of results (default 5)
            chunkSize: int - Chunk size (default 500)
            chunkOverlap: int - Chunk overlap (default 50)
            enableBm25: bool - Use hybrid search (default True)
            systemPrompt: str - Optional system prompt override
            model: str - LLM model for generation (optional)
            temperature: float - Generation temperature (default 0.3)
            maxTokens: int - Max generation tokens (default 1024)

        Returns:
            Dict with output, query, sources, chunks, retrievalTimeMs.
        """
        from agentweave.rag.pipeline import RAGPipeline
        from agentweave.rag.types import Document
        from agentweave.rag.vectorstore.in_memory import InMemoryVectorStore
        from agentweave.rag.chunking.recursive import RecursiveCharacterChunker
        from app.config import get_settings

        settings = get_settings()
        data = node.data or {}

        # Get query from upstream input
        query = self._resolve_input(node, context)
        if not query or not query.strip():
            return {
                "output": "No query provided to RAG node.",
                "query": "",
                "sources": [],
                "chunks": [],
                "retrievalTimeMs": 0,
            }

        try:
            # Create LLM provider for generation
            model = data.get("model") or settings.default_llm_model
            llm_provider = self._create_llm_provider(model, settings)

            # Create embedding provider from config
            embedding = self._create_embedding_provider(settings)

            # Build pipeline
            pipeline = RAGPipeline(
                llm=llm_provider,
                embedding_provider=embedding,
                vectorstore=InMemoryVectorStore(),
                chunker=RecursiveCharacterChunker(
                    chunk_size=data.get("chunkSize", 500),
                    chunk_overlap=data.get("chunkOverlap", 50),
                ),
                search_limit=data.get("searchLimit", 5),
                enable_bm25=data.get("enableBm25", True),
                system_prompt=data.get("systemPrompt") or None,
            )

            # Ingest documents
            documents = data.get("documents", [])
            if documents:
                docs = [
                    Document(id=f"doc-{i}", content=doc_text)
                    for i, doc_text in enumerate(documents)
                    if doc_text and doc_text.strip()
                ]
                if docs:
                    await pipeline.ingest_documents(docs)

            # Query
            async with pipeline:
                response = await pipeline.query(
                    query,
                    temperature=data.get("temperature", 0.3),
                    max_tokens=data.get("maxTokens", 1024),
                )

            return {
                "output": response.answer,
                "query": query,
                "sources": response.source_documents,
                "chunks": [
                    {"content": r.chunk.content, "score": r.score}
                    for r in response.retrieval.results
                ],
                "retrievalTimeMs": response.retrieval.total_ms,
            }

        except Exception as e:
            logger.error(f"RAG node {node.id} failed: {e}")
            return {
                "output": f"RAG execution failed: {str(e)}",
                "query": query,
                "sources": [],
                "chunks": [],
                "retrievalTimeMs": 0,
                "error": str(e),
            }

    async def _run_multi_agent(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a multi-agent team node.

        Uses AgentWeave's AgentTeam to coordinate multiple agents.

        Node data fields:
            name: str - Team name
            members: list[dict] - Agent configurations with name, role, model, temperature, systemPrompt
            strategy: str - Orchestration strategy (coordinator, round_robin, debate, map_reduce)
            maxRounds: int - Maximum orchestration rounds (default 10)

        Returns:
            Dict with output, strategy, rounds, totalCost, totalTokens, agentOutputs, messageCount.
        """
        from agentweave import Agent, AgentTeam
        from app.config import get_settings

        settings = get_settings()
        data = node.data if isinstance(node.data, dict) else {}

        # Build agents from member configs
        agents = []
        for member_config in data.get("members", []):
            model = member_config.get("model", settings.default_llm_model)
            provider = self._create_llm_provider(model, settings)

            agent = Agent(
                name=member_config.get("name", "agent"),
                role=member_config.get("role", "worker"),
                model=model,
                temperature=member_config.get("temperature", 0.7),
                system_prompt=member_config.get("systemPrompt", ""),
                llm_provider=provider,
            )
            agents.append(agent)

        if not agents:
            return {"output": "No agents configured", "error": "Empty team"}

        # Create team
        strategy = data.get("strategy", "coordinator")
        max_rounds = data.get("maxRounds", 10)

        team = AgentTeam(
            name=data.get("name", "team"),
            members=agents,
            strategy=strategy,
            max_rounds=max_rounds,
        )

        # Resolve input from context
        input_text = self._resolve_input(node, context)

        try:
            result = await team.run(input_text)

            # Store token usage
            # Note: Multi-agent aggregation doesn't track prompt/completion separately
            context[f"_usage_{node.id}"] = {
                "prompt_tokens": 0,  # Not tracked separately in multi-agent mode
                "completion_tokens": 0,  # Not tracked separately in multi-agent mode
                "total_tokens": result.total_tokens,
                "cost": result.total_cost,
                "model": f"multi-agent-{strategy}",
            }

            return {
                "output": result.output,
                "strategy": result.strategy,
                "rounds": result.rounds,
                "totalCost": result.total_cost,
                "totalTokens": result.total_tokens,
                "agentOutputs": {
                    name: {"output": ao.output, "tokens": ao.tokens, "cost": ao.cost}
                    for name, ao in result.agent_outputs.items()
                },
                "messageCount": len(result.messages),
            }
        finally:
            await team.close()

    @staticmethod
    def _create_llm_provider(model: str, settings) -> "BaseLLMProvider":
        """Create LLM provider with API key from application config.

        Args:
            model: Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet').
            settings: Application settings with API keys.

        Returns:
            Configured LLM provider.

        Raises:
            ValueError: If no API key configured for the detected provider.
        """
        if model.startswith(("gpt-", "o1", "o3", "o4", "text-")):
            if not settings.openai_api_key:
                raise ValueError(
                    f"OpenAI API key not configured. Set OPENAI_API_KEY to use model '{model}'."
                )
            from agentweave.llm.openai import OpenAIProvider
            return OpenAIProvider(
                model=model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
                timeout=settings.llm_timeout,
            )
        elif model.startswith("claude-"):
            if not settings.anthropic_api_key:
                raise ValueError(
                    f"Anthropic API key not configured. Set ANTHROPIC_API_KEY to use model '{model}'."
                )
            from agentweave.llm.anthropic import AnthropicProvider
            return AnthropicProvider(
                model=model,
                api_key=settings.anthropic_api_key,
                timeout=settings.llm_timeout,
            )
        elif model.startswith("gemini"):
            if not settings.gemini_api_key:
                raise ValueError(
                    f"Gemini API key not configured. Set GEMINI_API_KEY to use model '{model}'."
                )
            from agentweave.llm.gemini import GeminiProvider
            return GeminiProvider(
                model=model,
                api_key=settings.gemini_api_key,
                timeout=settings.llm_timeout,
            )
        elif model in ("llama3.1", "llama3.1:70b", "llama3.2", "llama3.3", "mistral", "codellama", "qwen2.5", "deepseek-r1", "phi-4", "gemma2") or model.startswith("ollama/"):
            from agentweave.llm.ollama import OllamaProvider
            actual_model = model.replace("ollama/", "")
            return OllamaProvider(
                model=actual_model,
                base_url=settings.ollama_base_url,
                timeout=settings.llm_timeout,
            )
        else:
            raise ValueError(
                f"Unsupported model: '{model}'. Use gpt-*/o1*/o3*/o4* for OpenAI, claude-* for Anthropic, "
                f"gemini-* for Gemini, or use 'ollama/<model>' prefix for Ollama."
            )

    @staticmethod
    def _create_embedding_provider(settings) -> "EmbeddingProvider":
        """Create embedding provider with API key from application config.

        Falls back to hash-based embedding if no API key is configured.

        Args:
            settings: Application settings with API keys and embedding config.

        Returns:
            Configured embedding provider or hash-based fallback.
        """
        provider = settings.embedding_provider.lower()

        if provider == "openai":
            if not settings.openai_api_key:
                logger.warning(
                    "OpenAI API key not configured. Falling back to hash-based embedding."
                )
                return _HashEmbeddingProvider()
            from agentweave.rag.embeddings.openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.embedding_model,
                api_key=settings.openai_api_key,
                dimensions=settings.embedding_dimensions,
            )
        elif provider == "ollama":
            from agentweave.rag.embeddings.ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=settings.embedding_model,
                base_url=settings.ollama_base_url,
                dimensions=settings.embedding_dimensions,
            )
        else:
            # "hash" or unknown provider -> fallback
            return _HashEmbeddingProvider()

    async def _run_mcp_tool(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> Any:
        """Execute MCP tool node."""
        data = node.data

        # Resolve secrets and templates in parameters
        parameters = data.get("parameters", {})
        resolved_params = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                # First resolve templates, then secrets
                resolved = self._resolve_template(value, context)
                resolved_params[key] = await self.secret_store.resolve(resolved)
            else:
                resolved_params[key] = value

        # Execute tool
        result = await self.mcp_manager.execute_tool(
            server_id=data["serverId"],
            tool_name=data["toolName"],
            arguments=resolved_params,
        )

        return result

    async def _run_condition(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute condition node with safe expression evaluation.

        Returns dict with 'result' (bool) and 'active_handle' ('true' or 'false').
        """
        from simpleeval import EvalWithCompoundTypes, InvalidExpression

        data = node.data
        condition = data.get("condition", "true")

        # Get previous node output
        prev_output = self._resolve_input(node, context)

        # Build sanitized context - only expose public node outputs
        safe_context = {
            k: v for k, v in context.items()
            if not k.startswith("_") and k != "input"
        }

        # Safe evaluation with whitelisted functions
        safe_names: dict[str, Any] = {
            "input": prev_output,
            "context": safe_context,
            "true": True,
            "false": False,
            "none": None,
            "True": True,
            "False": False,
            "None": None,
        }
        safe_functions = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "abs": abs,
            "min": min,
            "max": max,
            "any": any,
            "all": all,
        }

        try:
            evaluator = EvalWithCompoundTypes(
                names=safe_names,
                functions=safe_functions,
            )
            result = bool(evaluator.eval(condition))
        except (InvalidExpression, Exception) as e:
            # Default to False on evaluation error, log the issue
            logger.warning(f"Condition evaluation error for node {node.id}: {e}")
            result = False

        return {
            "result": result,
            "active_handle": "true" if result else "false",
        }

    async def _run_feedback_loop(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
        mode: str,
    ) -> dict[str, Any]:
        """Execute feedback loop node.

        Evaluates exit condition and tracks iteration count.
        Returns dict with iteration info and whether to continue looping.
        """
        from simpleeval import EvalWithCompoundTypes

        data = node.data
        max_iterations = data.get("maxIterations", 10)
        exit_condition = data.get("exitCondition", "false")

        # Get iteration count from context
        loop_key = f"_loop_{node.id}"
        iteration = context.get(loop_key, 0)

        # Check max iterations
        if iteration >= max_iterations:
            return {
                "continue_loop": False,
                "iteration": iteration,
                "reason": "max_iterations_reached",
            }

        # Evaluate exit condition
        prev_output = self._resolve_input(node, context)

        # Build sanitized context - only expose public node outputs
        safe_context = {
            k: v for k, v in context.items()
            if not k.startswith("_") and k != "input"
        }

        safe_names: dict[str, Any] = {
            "input": prev_output,
            "context": safe_context,
            "iteration": iteration,
            "true": True,
            "false": False,
        }
        safe_functions = {
            "len": len, "str": str, "int": int, "float": float,
            "bool": bool, "abs": abs,
        }

        try:
            evaluator = EvalWithCompoundTypes(names=safe_names, functions=safe_functions)
            should_exit = bool(evaluator.eval(exit_condition))
        except Exception as e:
            logger.warning(f"Feedback loop exit condition eval error for node {node.id}: {e}")
            should_exit = False

        if should_exit:
            return {
                "continue_loop": False,
                "iteration": iteration,
                "reason": "exit_condition_met",
            }

        # Increment iteration
        context[loop_key] = iteration + 1

        return {
            "continue_loop": True,
            "iteration": iteration + 1,
            "reason": "continuing",
        }

    async def _build_agent_tools(self, mcp_tool_ids: list[str]) -> list:
        """Convert MCP tool IDs to agentweave Tool objects.

        Args:
            mcp_tool_ids: List of "serverId:toolName" strings.

        Returns:
            List of Tool objects for the Agent.
        """
        if not mcp_tool_ids:
            return []

        from agentweave.tools.base import Tool, ToolParameter

        tools = []
        for tool_id in mcp_tool_ids:
            parts = tool_id.split(":", 1)
            if len(parts) != 2:
                logger.warning("Invalid MCP tool ID format: %s (expected 'serverId:toolName')", tool_id)
                continue

            server_id, tool_name = parts

            # Find MCPTool metadata
            mcp_tool = self._find_mcp_tool(server_id, tool_name)
            if not mcp_tool:
                logger.warning("MCP tool not found: %s:%s", server_id, tool_name)
                continue

            # Convert JSON Schema parameters to ToolParameter list
            params = self._schema_to_tool_params(mcp_tool.input_schema)

            # Create wrapper function that calls MCP manager
            # Use default args to capture server_id/tool_name in closure
            async def mcp_func(
                _sid: str = server_id,
                _tn: str = tool_name,
                **kwargs: Any,
            ) -> Any:
                return await self.mcp_manager.execute_tool(_sid, _tn, kwargs)

            tools.append(Tool(
                name=f"{server_id}__{tool_name}",
                description=mcp_tool.description,
                parameters=params,
                func=mcp_func,
            ))

        return tools

    def _find_mcp_tool(self, server_id: str, tool_name: str):
        """Find an MCPTool by server_id and tool_name."""
        server_tools = self.mcp_manager._tools.get(server_id, [])
        for tool in server_tools:
            if tool.name == tool_name:
                return tool
        return None

    @staticmethod
    def _schema_to_tool_params(schema: dict[str, Any]) -> list:
        """Convert JSON Schema to ToolParameter list."""
        from agentweave.tools.base import ToolParameter

        params = []
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        for name, prop in properties.items():
            param_type = prop.get("type", "string")
            params.append(ToolParameter(
                name=name,
                type=param_type,
                description=prop.get("description", ""),
                required=name in required_fields,
                default=prop.get("default"),
                enum=prop.get("enum"),
            ))

        return params

    def _get_mock_output(self, node: WorkflowNode) -> Any:
        """Get mock output for node."""
        if node.type == "agent":
            return f"[Mock] Agent \'{node.data.get('name', 'Agent')}\' response"
        elif node.type == "mcp_tool":
            tool_name = node.data.get("toolName", "unknown")
            if "mockResponse" in node.data:
                return node.data["mockResponse"]
            return {"result": f"[Mock] {tool_name} output"}
        elif node.type == "condition":
            return {"result": True, "active_handle": "true"}
        elif node.type == "parallel":
            return {"parallel": True, "branches": len(node.data.get("branches", []))}
        elif node.type == "feedback_loop":
            return {"continue_loop": False, "iteration": 0, "reason": "mock_mode"}
        elif node.type == "rag":
            return {
                "output": "[Mock] RAG answer based on indexed documents",
                "query": "[Mock] Query",
                "sources": ["doc-0"],
                "chunks": [{"content": "[Mock] Retrieved chunk", "score": 0.95}],
                "retrievalTimeMs": 100,
            }
        elif node.type == "multi_agent":
            data = node.data if isinstance(node.data, dict) else {}
            return {
                "output": f"[Mock] Multi-agent output for team '{data.get('name', 'team')}'",
                "strategy": data.get("strategy", "coordinator"),
                "rounds": 1,
                "totalCost": 0.0,
                "totalTokens": 0,
                "agentOutputs": {},
                "messageCount": 0,
            }
        return None

    def _resolve_template(self, template: str, context: dict[str, Any]) -> str:
        """Resolve {{nodeId.field.subfield}} templates from execution context.

        Args:
            template: String containing template patterns.
            context: Execution context with node outputs.

        Returns:
            String with resolved templates.
        """
        def replacer(match: re.Match) -> str:
            path = match.group(1).split(".")
            node_id = path[0]
            if node_id not in context:
                return match.group(0)  # Leave unresolved
            value = context[node_id]
            for key in path[1:]:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return match.group(0)  # Can't traverse further
            return str(value)
        return self.TEMPLATE_PATTERN.sub(replacer, template)

    def _resolve_input(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> str:
        """Resolve input for node from context with template support."""
        # Check for explicit inputSource
        input_source = node.data.get("inputSource")
        if input_source and input_source in context:
            raw = str(context[input_source])
        else:
            raw = str(context.get("input", ""))

        # Also check for inputTemplate in node data
        input_template = node.data.get("inputTemplate")
        if input_template:
            return self._resolve_template(input_template, context)

        # Apply template resolution to raw input (in case it contains {{...}})
        return self._resolve_template(raw, context)

    def _get_node_timeout(self, node: WorkflowNode) -> float:
        """Get timeout for node type."""
        if node.type == "agent":
            return self.DEFAULT_NODE_TIMEOUT
        elif node.type == "mcp_tool":
            return self.DEFAULT_TOOL_TIMEOUT
        elif node.type in ("parallel", "feedback_loop"):
            return self.DEFAULT_WORKFLOW_TIMEOUT  # Allow more time
        return self.DEFAULT_NODE_TIMEOUT

    def _validate_workflow(self, workflow: Workflow) -> None:
        """Validate workflow before execution.

        Raises:
            WorkflowValidationError: If workflow is invalid.
        """
        # Check node count
        if len(workflow.nodes) > 100:
            raise WorkflowValidationError(
                f"Workflow has {len(workflow.nodes)} nodes, maximum is 100"
            )

        # Check for cycles
        if self._has_cycle(workflow):
            raise WorkflowValidationError("Workflow contains a cycle")

        # Check for orphan nodes (not connected)
        orphans = self._find_orphan_nodes(workflow)
        if orphans:
            raise WorkflowValidationError(
                f"Workflow has orphan nodes: {orphans}"
            )

    def _has_cycle(self, workflow: Workflow) -> bool:
        """Check if workflow has unauthorized cycles.

        Cycles through feedback_loop nodes are allowed (controlled iteration).
        Only pure cycles without feedback_loop are rejected.
        """
        # Identify feedback_loop nodes
        feedback_nodes = {n.id for n in workflow.nodes if n.type == "feedback_loop"}

        adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.source in adjacency:
                adjacency[edge.source].append(edge.target)

        # Remove edges FROM feedback_loop nodes for cycle detection
        # (these are the "back edges" that create intentional loops)
        filtered_adjacency: dict[str, list[str]] = {}
        for node_id, neighbors in adjacency.items():
            if node_id in feedback_nodes:
                # Remove all outgoing edges from feedback nodes for cycle check
                filtered_adjacency[node_id] = []
            else:
                filtered_adjacency[node_id] = neighbors

        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in filtered_adjacency.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node in workflow.nodes:
            if node.id not in visited:
                if dfs(node.id):
                    return True

        return False

    def _find_orphan_nodes(self, workflow: Workflow) -> list[str]:
        """Find nodes with no connections."""
        if len(workflow.nodes) <= 1:
            return []

        connected: set[str] = set()
        for edge in workflow.edges:
            connected.add(edge.source)
            connected.add(edge.target)

        orphans = [n.id for n in workflow.nodes if n.id not in connected]
        return orphans

    def _find_error_edge_target(self, node_id: str, workflow: Workflow) -> str | None:
        """Find the target node for an error edge from the given node.

        Args:
            node_id: Source node ID.
            workflow: Workflow definition.

        Returns:
            Target node ID if an error edge exists, None otherwise.
        """
        for edge in workflow.edges:
            if edge.source == node_id and edge.source_handle == "error":
                return edge.target
        return None

    def _topological_sort(self, workflow: Workflow) -> list[WorkflowNode]:
        """Sort nodes in execution order.

        For workflows with feedback_loop nodes, edges from feedback_loop
        nodes that point backward are excluded to break cycles for sorting.
        """
        feedback_nodes = {n.id for n in workflow.nodes if n.type == "feedback_loop"}

        node_map = {n.id: n for n in workflow.nodes}
        in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}
        adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}

        for edge in workflow.edges:
            # Skip back-edges from feedback_loop nodes for topological sorting
            if edge.source in feedback_nodes:
                continue
            if edge.target in in_degree:
                in_degree[edge.target] += 1
            if edge.source in adjacency:
                adjacency[edge.source].append(edge.target)

        # Start with nodes that have no incoming edges
        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        result: list[WorkflowNode] = []

        while queue:
            node_id = queue.popleft()
            result.append(node_map[node_id])

            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _aggregate_token_usage(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregate token usage from all agent nodes in context."""
        total_prompt = 0
        total_completion = 0
        total_cost = 0.0
        model = None

        for key, value in context.items():
            if key.startswith("_usage_") and isinstance(value, dict):
                total_prompt += value.get("prompt_tokens", 0)
                total_completion += value.get("completion_tokens", 0)
                total_cost += value.get("cost", 0.0)
                if not model:
                    model = value.get("model")

        if total_prompt + total_completion == 0:
            return {}

        return {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "estimated_cost": round(total_cost, 6),
            "model_used": model,
        }

    def stop(self, execution_id: str) -> None:
        """Stop running execution."""
        # Mark execution as cancelled
        self._cancelled.add(execution_id)

        # Also cancel the task if it exists
        if execution_id in self._running:
            self._running[execution_id].cancel()
            del self._running[execution_id]

    async def resume(self, execution_id: str, workflow: Workflow, mode: str = "mock") -> WorkflowExecution:
        """Resume execution from checkpoint.

        Args:
            execution_id: Execution to resume.
            workflow: Workflow definition.
            mode: Execution mode ("full", "mock", "debug").

        Returns:
            Continued execution result.
        """
        state = await self.state_store.load_state(execution_id)
        if not state:
            raise ValueError(f"No saved state for execution {execution_id}")

        result = await self.run(
            workflow=workflow,
            input=state["context"].get("input", ""),
            mode=mode,
            start_from_node=state["current_node"],
            context=state["context"],
        )

        # Clean up original checkpoint on successful resume
        if result.status == ExecutionStatus.COMPLETED:
            await self.state_store.delete_state(execution_id)

        return result
