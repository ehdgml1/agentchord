"""Executions API endpoints.

Phase 0 MVP:
- List executions
- Get execution details
- Stop/resume execution
- Get execution logs
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..auth.jwt import User
from ..core.rbac import require_permission
from ..db.database import get_db
from ..dtos.execution import (
    ExecutionDetailResponse,
    ExecutionListItemResponse,
    ExecutionListResponsePydantic,
    NodeLogResponse,
)
from ..services.execution_service import (
    ExecutionNotFoundError,
    ExecutionNotResumableError,
    ExecutionNotStoppableError,
    ExecutionService,
)


router = APIRouter(prefix="/api/executions", tags=["executions"])


# Module-level connection tracker
_sse_connections: dict[str, int] = {}
_MAX_SSE_PER_USER = 5


async def _track_sse_connection(user_id: str):
    """Track SSE connection count per user."""
    count = _sse_connections.get(user_id, 0)
    if count >= _MAX_SSE_PER_USER:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "TOO_MANY_CONNECTIONS",
                    "message": f"Maximum {_MAX_SSE_PER_USER} SSE connections per user"
                }
            }
        )
    _sse_connections[user_id] = count + 1


def _release_sse_connection(user_id: str):
    """Release SSE connection count."""
    count = _sse_connections.get(user_id, 0)
    if count <= 1:
        _sse_connections.pop(user_id, None)
    else:
        _sse_connections[user_id] = count - 1


def _get_execution_service_from_app(request: Request, session: AsyncSession) -> ExecutionService:
    """Get execution service using app.state singletons."""
    from ..repositories.execution_repo import ExecutionRepository
    from ..repositories.workflow_repo import WorkflowRepository

    execution_repo = ExecutionRepository(session)
    workflow_repo = WorkflowRepository(session)

    return ExecutionService(
        executor=request.app.state.executor,
        execution_repo=execution_repo,
        workflow_repo=workflow_repo,
        state_store=request.app.state.executor.state_store,
    )


@router.get("", response_model=ExecutionListResponsePydantic)
@require_permission("execution:read")
async def list_executions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workflow_id: str | None = Query(None, description="Filter by workflow ID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List executions for current user.

    Args:
        user: Current authenticated user.
        session: Database session.
        workflow_id: Optional workflow ID filter.
        status: Optional status filter.
        limit: Maximum number of executions to return.
        offset: Number of executions to skip.

    Returns:
        List of executions with pagination.
    """
    from sqlalchemy import func, select
    from ..models.execution import Execution
    from ..models.workflow import Workflow as WorkflowModel

    # Use subquery to avoid materializing workflow IDs in Python
    wf_subq = select(WorkflowModel.id).where(
        (WorkflowModel.owner_id == user.id) | (WorkflowModel.owner_id.is_(None))
    ).scalar_subquery()

    stmt = select(Execution).where(
        Execution.workflow_id.in_(wf_subq)
    ).order_by(Execution.started_at.desc())
    if workflow_id:
        stmt = stmt.where(Execution.workflow_id == workflow_id)
    if status:
        stmt = stmt.where(Execution.status == status)

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

    return ExecutionListResponsePydantic(
        executions=[
            ExecutionListItemResponse(
                id=e.id,
                workflow_id=e.workflow_id,
                status=e.status,
                mode=e.mode,
                trigger_type=e.trigger_type,
                started_at=e.started_at.isoformat() if e.started_at else None,
                completed_at=e.completed_at.isoformat() if e.completed_at else None,
                duration_ms=e.duration_ms,
                total_tokens=e.total_tokens,
                estimated_cost=e.estimated_cost,
            )
            for e in paginated
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
@require_permission("execution:read")
async def get_execution(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Get execution details including node logs.

    Args:
        execution_id: Execution ID.
        user: Current authenticated user.
        session: Database session.

    Returns:
        Detailed execution information.

    Raises:
        404: Execution not found.
    """
    import json
    from ..repositories.execution_repo import ExecutionRepository
    from ..models.workflow import Workflow as WorkflowModel

    repo = ExecutionRepository(session)
    execution = await repo.get_by_id(execution_id)

    if not execution:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution '{execution_id}' not found",
                }
            },
        )

    # Authorization check via workflow ownership
    wf = await session.get(WorkflowModel, execution.workflow_id)
    if wf and wf.owner_id and wf.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this execution"}},
        )

    node_logs_data = json.loads(execution.node_logs or "[]")

    return ExecutionDetailResponse(
        id=execution.id,
        workflow_id=execution.workflow_id,
        status=execution.status,
        mode=execution.mode,
        trigger_type=execution.trigger_type,
        trigger_id=execution.trigger_id,
        input=execution.input,
        output=json.loads(execution.output) if execution.output else None,
        error=execution.error,
        node_logs=[NodeLogResponse(**log) for log in node_logs_data],
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        duration_ms=execution.duration_ms,
        total_tokens=execution.total_tokens,
        prompt_tokens=execution.prompt_tokens,
        completion_tokens=execution.completion_tokens,
        estimated_cost=execution.estimated_cost,
        model_used=execution.model_used,
    )


@router.post("/{execution_id}/stop", status_code=200)
@require_permission("execution:write")
async def stop_execution(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Stop running execution.

    Args:
        execution_id: Execution ID.
        user: Current authenticated user.
        session: Database session.
        request: FastAPI request object.

    Returns:
        Success message with execution details.

    Raises:
        404: Execution not found.
        403: Access denied.
        400: Execution not in stoppable state.
    """
    from ..repositories.execution_repo import ExecutionRepository
    from ..models.workflow import Workflow as WorkflowModel

    repo = ExecutionRepository(session)
    execution = await repo.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail={"error": {"code": "EXECUTION_NOT_FOUND", "message": f"Execution '{execution_id}' not found"}})

    wf = await session.get(WorkflowModel, execution.workflow_id)
    if wf and wf.owner_id and wf.owner_id != user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this execution"}})

    service = _get_execution_service_from_app(request, session)

    try:
        execution = await service.stop_execution(execution_id)
        return {
            "message": "Execution stopped",
            "execution_id": execution.id,
            "status": execution.status,
        }
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution '{execution_id}' not found",
                }
            },
        )
    except ExecutionNotStoppableError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "EXECUTION_NOT_STOPPABLE",
                    "message": str(e),
                }
            },
        )


@router.post("/{execution_id}/resume", status_code=200)
@require_permission("execution:write")
async def resume_execution(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Resume paused or failed execution.

    Args:
        execution_id: Execution ID.
        user: Current authenticated user.
        session: Database session.
        request: FastAPI request object.

    Returns:
        Success message with execution details.

    Raises:
        404: Execution not found.
        403: Access denied.
        400: Execution not in resumable state.
    """
    from ..repositories.execution_repo import ExecutionRepository
    from ..models.workflow import Workflow as WorkflowModel

    repo = ExecutionRepository(session)
    execution = await repo.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail={"error": {"code": "EXECUTION_NOT_FOUND", "message": f"Execution '{execution_id}' not found"}})

    wf = await session.get(WorkflowModel, execution.workflow_id)
    if wf and wf.owner_id and wf.owner_id != user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this execution"}})

    service = _get_execution_service_from_app(request, session)

    try:
        execution = await service.resume_execution(execution_id)
        return {
            "message": "Execution resumed",
            "execution_id": execution.id,
            "status": execution.status,
        }
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution '{execution_id}' not found",
                }
            },
        )
    except ExecutionNotResumableError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "EXECUTION_NOT_RESUMABLE",
                    "message": str(e),
                }
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "RESUME_FAILED",
                    "message": str(e),
                }
            },
        )


@router.get("/{execution_id}/logs", response_model=list[NodeLogResponse])
@require_permission("execution:read")
async def get_execution_logs(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    node_id: str | None = Query(None, description="Filter by node ID"),
):
    """Get execution logs.

    Args:
        execution_id: Execution ID.
        user: Current authenticated user.
        session: Database session.
        request: FastAPI request object.
        node_id: Optional node ID filter.

    Returns:
        List of node execution logs.

    Raises:
        404: Execution not found.
        403: Access denied.
    """
    from ..repositories.execution_repo import ExecutionRepository
    from ..models.workflow import Workflow as WorkflowModel

    repo = ExecutionRepository(session)
    execution = await repo.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail={"error": {"code": "EXECUTION_NOT_FOUND", "message": f"Execution '{execution_id}' not found"}})

    wf = await session.get(WorkflowModel, execution.workflow_id)
    if wf and wf.owner_id and wf.owner_id != user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this execution"}})

    service = _get_execution_service_from_app(request, session)

    try:
        logs = await service.get_execution_logs(execution_id, node_id)
        return [NodeLogResponse(**log) for log in logs]
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution '{execution_id}' not found",
                }
            },
        )


@router.get("/{execution_id}/stream")
@require_permission("execution:read")
async def stream_execution_events(
    execution_id: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Stream execution events via Server-Sent Events.

    Args:
        execution_id: Execution ID.
        request: FastAPI request object.
        user: Current authenticated user.
        session: Database session.

    Returns:
        StreamingResponse with SSE events.

    Raises:
        404: Execution not found.
        403: Access denied.
    """
    from ..repositories.execution_repo import ExecutionRepository
    from ..models.workflow import Workflow as WorkflowModel

    repo = ExecutionRepository(session)
    execution = await repo.get_by_id(execution_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "EXECUTION_NOT_FOUND", "message": f"Execution '{execution_id}' not found"}},
        )

    wf = await session.get(WorkflowModel, execution.workflow_id)
    if wf and wf.owner_id and wf.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You do not have access to this execution"}},
        )

    bg_executor = request.app.state.bg_executor

    # Track SSE connection for rate limiting
    await _track_sse_connection(user.id)

    async def event_generator():
        try:
            # Send existing events first
            for event in bg_executor.get_events(execution_id):
                data = json.dumps({
                    "type": event.event_type,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                })
                yield f"data: {data}\n\n"

            # If execution is no longer running, close
            if not bg_executor.is_running(execution_id):
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Subscribe to new events
            queue = bg_executor.subscribe(execution_id)
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        data = json.dumps({
                            "type": event.event_type,
                            "data": event.data,
                            "timestamp": event.timestamp.isoformat(),
                        })
                        yield f"data: {data}\n\n"

                        if event.event_type in ("completed", "failed"):
                            break
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield ": keepalive\n\n"
            finally:
                bg_executor.unsubscribe(execution_id, queue)
        finally:
            # Always release connection count
            _release_sse_connection(user.id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
