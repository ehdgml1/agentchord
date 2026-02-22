"""Playground API endpoints for chat interface.

Provides a simplified chat-oriented interface for workflow execution
with conversation history support.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..auth.jwt import User
from ..core.rbac import require_permission
from ..core.rate_limiter import limiter
from ..db.database import get_db
from ..repositories.workflow_repo import WorkflowRepository
from ..services.audit_service import AuditService
from ..services.execution_service import ExecutionService

router = APIRouter(prefix="/api/playground", tags=["playground"])


class ChatHistoryItem(BaseModel):
    """Single chat message in conversation history."""

    role: str = Field(..., pattern="^(user|assistant)$", description="Message role")
    content: str = Field(..., max_length=10000, description="Message content")


class PlaygroundChatRequest(BaseModel):
    """Playground chat request."""

    workflow_id: str = Field(..., description="Workflow ID to execute", alias="workflowId")
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    history: list[ChatHistoryItem] = Field(
        default_factory=list,
        max_length=100,
        description="Previous conversation history",
    )

    model_config = {"populate_by_name": True}


class PlaygroundChatResponse(BaseModel):
    """Playground chat response."""

    execution_id: str = Field(..., description="Execution ID", alias="executionId")
    status: str = Field(..., description="Execution status")

    model_config = {"populate_by_name": True}


@router.post("/chat", response_model=PlaygroundChatResponse)
@require_permission("workflow:write")
@limiter.limit("10/minute")
async def playground_chat(
    request_body: PlaygroundChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Execute workflow with chat context.

    This endpoint provides a simplified interface for chat-based workflow execution.
    It accepts a message and conversation history, builds enhanced context including
    the chat history, and executes the workflow in full mode.

    Args:
        request_body: Chat request with message and history.
        user: Current authenticated user.
        session: Database session.
        request: FastAPI request (for app state access).

    Returns:
        Execution details with execution_id and status.

    Raises:
        404: Workflow not found.
        403: User doesn't have access to workflow.
    """
    repo = WorkflowRepository(session)
    model = await repo.get_by_id(request_body.workflow_id)

    if not model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{request_body.workflow_id}' not found"
                }
            },
        )

    # Authorization check
    if model.owner_id and model.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this workflow"
                }
            },
        )

    # Build enhanced context with chat history
    context = {
        "input": request_body.message,
        "chat_history": [h.model_dump() for h in request_body.history],
    }

    # Create and dispatch execution via shared service
    executor = request.app.state.executor
    bg_executor = request.app.state.bg_executor
    exec_service = ExecutionService(executor=executor, execution_repo=None, workflow_repo=None, state_store=None)

    execution_id = await exec_service.create_and_dispatch(
        session=session,
        bg_executor=bg_executor,
        workflow_model=model,
        input_text=request_body.message,
        mode="full",
        trigger_type="playground",
        context=context,
        user_id=user.id,
    )

    # Audit log
    audit = AuditService(session)
    await audit.log(
        action="execute",
        resource_type="playground",
        resource_id=execution_id,
        user_id=user.id,
        details={"workflow_id": request_body.workflow_id, "trigger_type": "playground"},
    )

    return PlaygroundChatResponse(
        execution_id=execution_id,
        status="running",
    )
