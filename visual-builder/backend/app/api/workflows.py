"""Workflows API endpoints.

Phase 4: Workflow CRUD API connected to database.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..auth.jwt import User
from ..core.rbac import require_permission
from ..core.rate_limiter import limiter
from ..db.database import get_db
from ..dtos.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowValidateResponse,
    WorkflowValidationError as WorkflowValidationErrorDTO,
    WorkflowNode as WorkflowNodeDTO,
    WorkflowEdge as WorkflowEdgeDTO,
)
from ..models.workflow import Workflow as WorkflowModel
from ..repositories.workflow_repo import WorkflowRepository

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _model_to_response(model: WorkflowModel) -> WorkflowResponse:
    """Convert SQLAlchemy model to response DTO."""
    nodes_data = json.loads(model.nodes) if isinstance(model.nodes, str) else model.nodes
    edges_data = json.loads(model.edges) if isinstance(model.edges, str) else model.edges

    return WorkflowResponse(
        id=model.id,
        name=model.name,
        description=model.description or "",
        nodes=[WorkflowNodeDTO(**n) for n in nodes_data] if nodes_data else [],
        edges=[WorkflowEdgeDTO(**e) for e in edges_data] if edges_data else [],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("", response_model=WorkflowListResponse)
@require_permission("workflow:read")
async def list_workflows(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List workflows owned by current user.

    Args:
        user: Current authenticated user.
        limit: Maximum number of workflows to return.
        offset: Number of workflows to skip.

    Returns:
        List of workflows with pagination.
    """
    from sqlalchemy import func, select

    # Build query with SQL WHERE clause
    stmt = select(WorkflowModel).where(
        (WorkflowModel.owner_id == user.id) | (WorkflowModel.owner_id.is_(None))
    ).order_by(WorkflowModel.created_at.desc())

    # Count query
    count_stmt = select(func.count()).select_from(
        stmt.subquery()
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Paginated query
    paginated_stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(paginated_stmt)
    paginated = list(result.scalars().all())

    return WorkflowListResponse(
        workflows=[_model_to_response(w) for w in paginated],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WorkflowResponse, status_code=201)
@require_permission("workflow:write")
async def create_workflow(
    workflow: WorkflowCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Create new workflow.

    Args:
        workflow: Workflow creation data.
        user: Current authenticated user.

    Returns:
        Created workflow.
    """
    repo = WorkflowRepository(session)

    now = datetime.now(UTC).replace(tzinfo=None)
    model = WorkflowModel(
        id=str(uuid.uuid4()),
        name=workflow.name,
        description=workflow.description,
        nodes=json.dumps([n.model_dump() for n in workflow.nodes]),
        edges=json.dumps([e.model_dump(by_alias=True) for e in workflow.edges]),
        owner_id=user.id,
        created_at=now,
        updated_at=now,
    )

    created = await repo.create(model)
    return _model_to_response(created)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
@require_permission("workflow:read")
async def get_workflow(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Get workflow by ID.

    Args:
        workflow_id: Workflow ID.
        user: Current authenticated user.

    Returns:
        Workflow details.

    Raises:
        404: Workflow not found.
    """
    repo = WorkflowRepository(session)
    model = await repo.get_by_id(workflow_id)

    if not model:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow '{workflow_id}' not found"}},
        )

    # Authorization check
    if model.owner_id and model.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this workflow"}},
        )

    return _model_to_response(model)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
@require_permission("workflow:write")
async def update_workflow(
    workflow_id: str,
    workflow: WorkflowUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Update workflow.

    Args:
        workflow_id: Workflow ID.
        workflow: Workflow update data.
        user: Current authenticated user.

    Returns:
        Updated workflow.

    Raises:
        404: Workflow not found.
    """
    repo = WorkflowRepository(session)
    model = await repo.get_by_id(workflow_id)

    if not model:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow '{workflow_id}' not found"}},
        )

    # Authorization check
    if model.owner_id and model.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this workflow"}},
        )

    if workflow.name is not None:
        model.name = workflow.name
    if workflow.description is not None:
        model.description = workflow.description
    if workflow.nodes is not None:
        model.nodes = json.dumps([n.model_dump() for n in workflow.nodes])
    if workflow.edges is not None:
        model.edges = json.dumps([e.model_dump(by_alias=True) for e in workflow.edges])
    model.updated_at = datetime.now(UTC).replace(tzinfo=None)

    updated = await repo.update(model)
    return _model_to_response(updated)


@router.delete("/{workflow_id}", status_code=204)
@require_permission("workflow:write")
async def delete_workflow(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete workflow.

    Args:
        workflow_id: Workflow ID.
        user: Current authenticated user.

    Raises:
        404: Workflow not found.
    """
    repo = WorkflowRepository(session)
    model = await repo.get_by_id(workflow_id)

    if not model:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow '{workflow_id}' not found"}},
        )

    # Authorization check
    if model.owner_id and model.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this workflow"}},
        )

    deleted = await repo.delete(workflow_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow '{workflow_id}' not found"}},
        )


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
@require_permission("workflow:write")
@limiter.limit("10/minute")
async def run_workflow(
    workflow_id: str,
    request_body: WorkflowRunRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Execute workflow.

    Args:
        workflow_id: Workflow ID to execute.
        request_body: Execution parameters.
        user: Current authenticated user.

    Returns:
        Execution details.

    Raises:
        404: Workflow not found.
        400: Invalid workflow or execution request.
    """
    repo = WorkflowRepository(session)
    model = await repo.get_by_id(workflow_id)

    if not model:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow '{workflow_id}' not found"}},
        )

    # Authorization check
    if model.owner_id and model.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this workflow"}},
        )

    # Convert DB model to executor's Workflow dataclass
    from ..core.executor import (
        Workflow as ExecutorWorkflow,
        WorkflowNode,
        WorkflowEdge,
    )

    nodes_data = json.loads(model.nodes) if isinstance(model.nodes, str) else model.nodes
    edges_data = json.loads(model.edges) if isinstance(model.edges, str) else model.edges

    executor_workflow = ExecutorWorkflow(
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

    # Create initial execution record
    from ..models.execution import Execution as ExecutionModel
    from ..repositories.execution_repo import ExecutionRepository

    execution_id = str(uuid.uuid4())
    exec_repo = ExecutionRepository(session)

    now = datetime.now(UTC).replace(tzinfo=None)
    exec_model = ExecutionModel(
        id=execution_id,
        workflow_id=model.id,
        status="running",
        mode=request_body.mode,
        trigger_type="manual",
        input=request_body.input,
        started_at=now,
    )
    await exec_repo.create(exec_model)
    await session.commit()

    # Get executor and background executor from app state
    executor = request.app.state.executor
    bg_executor = request.app.state.bg_executor

    # Define background execution function
    async def _execute():
        from ..db.database import get_session_factory
        session_factory = get_session_factory()
        async with session_factory() as bg_session:
            bg_exec_repo = ExecutionRepository(bg_session)
            try:
                execution = await executor.run(
                    workflow=executor_workflow,
                    input=request_body.input,
                    mode=request_body.mode,
                )
                # Update execution record with results
                exec_record = await bg_exec_repo.get_by_id(execution_id)
                if exec_record:
                    exec_record.status = execution.status.value
                    exec_record.output = json.dumps(execution.output) if execution.output else None
                    exec_record.error = execution.error
                    exec_record.completed_at = execution.completed_at.replace(tzinfo=None) if execution.completed_at else None
                    if execution.completed_at and exec_record.started_at:
                        exec_record.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)

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
            except Exception as e:
                # Update execution record with error
                exec_record = await bg_exec_repo.get_by_id(execution_id)
                if exec_record:
                    exec_record.status = "failed"
                    exec_record.error = str(e)
                    exec_record.completed_at = datetime.now(UTC).replace(tzinfo=None)
                    if exec_record.started_at:
                        exec_record.duration_ms = int((datetime.now(UTC).replace(tzinfo=None) - exec_record.started_at).total_seconds() * 1000)
                    await bg_exec_repo.update(exec_record)
                    await bg_session.commit()

    # Dispatch to background
    await bg_executor.dispatch(_execute, execution_id)

    return WorkflowRunResponse(
        id=execution_id,
        workflow_id=model.id,
        status="running",
        mode=request_body.mode,
        trigger_type="manual",
        trigger_id=None,
        input=request_body.input,
        output=None,
        error=None,
        node_executions=[],
        started_at=now.isoformat(),
        completed_at=None,
        duration_ms=None,
    )


@router.post("/{workflow_id}/validate", response_model=WorkflowValidateResponse)
@require_permission("workflow:read")
async def validate_workflow(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Validate workflow without executing.

    Args:
        workflow_id: Workflow ID to validate.
        user: Current authenticated user.

    Returns:
        Validation result with errors if any.

    Raises:
        404: Workflow not found.
    """
    repo = WorkflowRepository(session)
    model = await repo.get_by_id(workflow_id)

    if not model:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow '{workflow_id}' not found"}},
        )

    # Authorization check
    if model.owner_id and model.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this workflow"}},
        )

    from ..core.executor import (
        Workflow as ExecutorWorkflow,
        WorkflowNode,
        WorkflowEdge,
        WorkflowValidationError,
    )

    nodes_data = json.loads(model.nodes) if isinstance(model.nodes, str) else model.nodes
    edges_data = json.loads(model.edges) if isinstance(model.edges, str) else model.edges

    executor_workflow = ExecutorWorkflow(
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

    executor = request.app.state.executor

    try:
        executor._validate_workflow(executor_workflow)
        return WorkflowValidateResponse(valid=True, errors=[])
    except WorkflowValidationError as e:
        return WorkflowValidateResponse(
            valid=False,
            errors=[WorkflowValidationErrorDTO(message=str(e))],
        )
