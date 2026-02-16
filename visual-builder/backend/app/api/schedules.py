"""Schedules API endpoints.

Phase -1 Implementation:
- CRUD operations for schedules
- Enable/disable toggle
- Filter by workflow_id
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.models.schedule import Schedule as ScheduleModel
from app.models.workflow import Workflow as WorkflowModel
from app.auth.jwt import User
from app.core.rbac import require_permission
from app.core.scheduler import (
    WorkflowScheduler,
    calculate_next_run,
    validate_cron_expression,
)
from app.db.database import get_db
from app.dtos.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
)
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.workflow_repo import WorkflowRepository

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

# Global scheduler instance (set during app startup)
_scheduler: WorkflowScheduler | None = None


def get_scheduler() -> WorkflowScheduler:
    """Get the global scheduler instance.

    Returns:
        WorkflowScheduler instance.

    Raises:
        HTTPException: If scheduler not initialized.
    """
    if _scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "SCHEDULER_NOT_READY",
                    "message": "Scheduler not initialized",
                }
            },
        )
    return _scheduler


def set_scheduler(scheduler: WorkflowScheduler) -> None:
    """Set the global scheduler instance.

    Called during app startup.

    Args:
        scheduler: WorkflowScheduler instance.
    """
    global _scheduler
    _scheduler = scheduler


def _schedule_to_response(schedule) -> ScheduleResponse:
    """Convert schedule model to response DTO.

    Args:
        schedule: Schedule model instance.

    Returns:
        ScheduleResponse DTO.
    """
    try:
        schedule_input = json.loads(schedule.input) if schedule.input else {}
    except json.JSONDecodeError:
        schedule_input = {}

    return ScheduleResponse(
        id=schedule.id,
        workflow_id=schedule.workflow_id,
        type=schedule.type,
        expression=schedule.expression,
        input=schedule_input,
        timezone=schedule.timezone,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.post("", response_model=ScheduleResponse, status_code=201)
@require_permission("schedule:write")
async def create_schedule(
    data: ScheduleCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scheduler: Annotated[WorkflowScheduler, Depends(get_scheduler)],
):
    """Create a new schedule for a workflow.

    Args:
        data: Schedule creation data.
        user: Current authenticated user.
        db: Database session.
        scheduler: Workflow scheduler.

    Returns:
        Created schedule.

    Raises:
        400: Invalid cron expression or timezone.
        404: Workflow not found.
        403: User doesn't own the workflow.
    """
    # Validate cron expression
    if not validate_cron_expression(data.expression):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_EXPRESSION",
                    "message": f"Invalid cron expression: {data.expression}",
                }
            },
        )

    # Validate timezone by attempting to calculate next run
    try:
        next_run = calculate_next_run(data.expression, data.timezone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_TIMEZONE",
                    "message": str(e),
                }
            },
        )

    # Verify workflow exists and user owns it
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(data.workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{data.workflow_id}' not found",
                }
            },
        )

    if workflow.owner_id and workflow.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this workflow",
                }
            },
        )

    # Create schedule
    schedule_repo = ScheduleRepository(db)
    schedule = await schedule_repo.create(
        workflow_id=data.workflow_id,
        expression=data.expression,
        input_data=data.input,
        timezone=data.timezone,
    )
    await schedule_repo.update_next_run(schedule.id, next_run)
    await db.commit()

    # Refresh to get updated next_run
    schedule = await schedule_repo.get_by_id(schedule.id)

    # Add to scheduler
    await scheduler.add_schedule(schedule)

    return _schedule_to_response(schedule)


@router.get("", response_model=ScheduleListResponse)
@require_permission("execution:read")
async def list_schedules(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    workflow_id: str | None = Query(None, description="Filter by workflow ID"),
):
    """List schedules owned by current user.

    Args:
        user: Current authenticated user.
        db: Database session.
        workflow_id: Optional workflow ID filter.

    Returns:
        List of schedules.
    """
    # Join schedules with workflows to filter by owner
    if workflow_id:
        # Verify user owns the workflow
        workflow_repo = WorkflowRepository(db)
        workflow = await workflow_repo.get_by_id(workflow_id)
        if not workflow or (workflow.owner_id and workflow.owner_id != user.id):
            # Return empty list instead of error to prevent enumeration
            return ScheduleListResponse(schedules=[], total=0)

        schedule_repo = ScheduleRepository(db)
        schedules = await schedule_repo.list_by_workflow(workflow_id)
    else:
        # List all schedules for workflows owned by user
        stmt = (
            select(ScheduleModel)
            .join(WorkflowModel, ScheduleModel.workflow_id == WorkflowModel.id)
            .where(WorkflowModel.owner_id == user.id)
            .order_by(ScheduleModel.created_at.desc())
        )
        result = await db.execute(stmt)
        schedules = list(result.scalars().all())

    return ScheduleListResponse(
        schedules=[_schedule_to_response(s) for s in schedules],
        total=len(schedules),
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
@require_permission("execution:read")
async def get_schedule(
    schedule_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get schedule by ID.

    Args:
        schedule_id: Schedule ID.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Schedule details.

    Raises:
        404: Schedule not found or user doesn't own it.
    """
    schedule_repo = ScheduleRepository(db)
    schedule = await schedule_repo.get_by_id(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(schedule.workflow_id)

    if not workflow:
        # Schedule exists but workflow is gone - return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    return _schedule_to_response(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
@require_permission("schedule:write")
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scheduler: Annotated[WorkflowScheduler, Depends(get_scheduler)],
):
    """Update schedule.

    Args:
        schedule_id: Schedule ID.
        data: Update data.
        user: Current authenticated user.
        db: Database session.
        scheduler: Workflow scheduler.

    Returns:
        Updated schedule.

    Raises:
        400: Invalid cron expression or timezone.
        404: Schedule not found or user doesn't own it.
    """
    schedule_repo = ScheduleRepository(db)
    schedule = await schedule_repo.get_by_id(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(schedule.workflow_id)

    if not workflow:
        # Schedule exists but workflow is gone - return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Validate new cron expression if provided
    expression = data.expression or schedule.expression
    timezone = data.timezone or schedule.timezone

    if data.expression and not validate_cron_expression(data.expression):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_EXPRESSION",
                    "message": f"Invalid cron expression: {data.expression}",
                }
            },
        )

    # Validate timezone
    try:
        next_run = calculate_next_run(expression, timezone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_TIMEZONE",
                    "message": str(e),
                }
            },
        )

    # Update schedule
    updated = await schedule_repo.update(
        schedule_id=schedule_id,
        expression=data.expression,
        input_data=data.input,
        timezone=data.timezone,
        enabled=data.enabled,
    )
    await schedule_repo.update_next_run(schedule_id, next_run)
    await db.commit()

    # Refresh schedule
    updated = await schedule_repo.get_by_id(schedule_id)

    # Update scheduler
    await scheduler.update_schedule(updated)

    return _schedule_to_response(updated)


@router.delete("/{schedule_id}", status_code=204)
@require_permission("schedule:write")
async def delete_schedule(
    schedule_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scheduler: Annotated[WorkflowScheduler, Depends(get_scheduler)],
):
    """Delete schedule.

    Args:
        schedule_id: Schedule ID.
        user: Current authenticated user.
        db: Database session.
        scheduler: Workflow scheduler.

    Raises:
        404: Schedule not found or user doesn't own it.
    """
    schedule_repo = ScheduleRepository(db)
    schedule = await schedule_repo.get_by_id(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(schedule.workflow_id)

    if not workflow:
        # Schedule exists but workflow is gone - return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Remove from scheduler first
    await scheduler.remove_schedule(schedule_id)

    # Delete from database
    deleted = await schedule_repo.delete(schedule_id)
    await db.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
@require_permission("schedule:write")
async def toggle_schedule(
    schedule_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scheduler: Annotated[WorkflowScheduler, Depends(get_scheduler)],
):
    """Toggle schedule enabled/disabled.

    Args:
        schedule_id: Schedule ID.
        user: Current authenticated user.
        db: Database session.
        scheduler: Workflow scheduler.

    Returns:
        Updated schedule with new enabled status.

    Raises:
        404: Schedule not found or user doesn't own it.
    """
    schedule_repo = ScheduleRepository(db)
    schedule = await schedule_repo.get_by_id(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(schedule.workflow_id)

    if not workflow:
        # Schedule exists but workflow is gone - return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found",
                }
            },
        )

    # Toggle enabled status
    new_enabled = not schedule.enabled
    await schedule_repo.update(schedule_id=schedule_id, enabled=new_enabled)

    # Update next_run if enabling
    if new_enabled:
        next_run = calculate_next_run(schedule.expression, schedule.timezone)
        await schedule_repo.update_next_run(schedule_id, next_run)
        await db.commit()

        schedule = await schedule_repo.get_by_id(schedule_id)
        await scheduler.enable_schedule(schedule)
    else:
        await schedule_repo.update_next_run(schedule_id, None)
        await db.commit()
        await scheduler.disable_schedule(schedule_id)

    schedule = await schedule_repo.get_by_id(schedule_id)
    return _schedule_to_response(schedule)
