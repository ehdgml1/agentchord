"""A/B Test API endpoints."""

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import User, get_current_user
from app.core.rbac import require_permission, Role
from app.db.database import get_db
from app.models.ab_test import ABTest, ABTestResult
from app.models.workflow import Workflow
from app.dtos.ab_test import (
    ABTestCreate,
    ABTestResponse,
    ABTestDetailResponse,
    ABTestStatsResponse,
    ABTestListResponse,
)
from app.core.ab_test_runner import ABTestRunner

router = APIRouter(prefix="/api/ab-tests", tags=["ab-tests"])


def _parse_metrics(raw: str) -> list[str]:
    """Parse metrics JSON safely.

    Args:
        raw: Raw JSON string.

    Returns:
        List of metric names, empty list if parse fails.
    """
    try:
        return json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []


@router.post("", response_model=ABTestResponse, status_code=201)
@require_permission("execution:write")
async def create_ab_test(
    data: ABTestCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Create A/B test.

    Args:
        data: Test creation request
        user: Current authenticated user
        db: Database session

    Returns:
        Created A/B test

    Raises:
        HTTPException: If workflows not found or user doesn't own them
    """
    # Verify workflows exist
    result = await db.execute(
        select(Workflow).where(
            Workflow.id.in_([data.workflow_a_id, data.workflow_b_id])
        )
    )
    workflows = result.scalars().all()
    if len(workflows) != 2:
        raise HTTPException(status_code=404, detail="One or both workflows not found")

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN:
        for workflow in workflows:
            if workflow.owner_id != user.id:
                raise HTTPException(status_code=404, detail="One or both workflows not found")

    # Create test
    test = ABTest(
        id=str(uuid.uuid4()),
        name=data.name,
        workflow_a_id=data.workflow_a_id,
        workflow_b_id=data.workflow_b_id,
        traffic_split=data.traffic_split,
        metrics=json.dumps(data.metrics),
        status="draft",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)

    return ABTestResponse(
        id=test.id,
        name=test.name,
        workflow_a_id=test.workflow_a_id,
        workflow_b_id=test.workflow_b_id,
        traffic_split=test.traffic_split,
        metrics=_parse_metrics(test.metrics),
        status=test.status,
        created_at=test.created_at.isoformat(),
        completed_at=test.completed_at.isoformat() if test.completed_at else None,
    )


@router.get("", response_model=ABTestListResponse)
@require_permission("execution:read")
async def list_ab_tests(
    user: Annotated[User, Depends(get_current_user)],
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List A/B tests.

    Args:
        user: Current authenticated user
        limit: Maximum number of tests to return
        offset: Offset for pagination
        db: Database session

    Returns:
        List of A/B tests (only those where user owns at least one workflow)
    """
    # Build base query joining with workflows to filter by ownership
    if user.role == Role.ADMIN:
        # Admins see all AB tests
        count_result = await db.execute(select(func.count(ABTest.id)))
        total = count_result.scalar() or 0

        result = await db.execute(
            select(ABTest)
            .order_by(ABTest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        tests = result.scalars().all()
    else:
        # Non-admins only see tests where they own at least one of the workflows
        # First get count
        count_query = (
            select(func.count(ABTest.id.distinct()))
            .join(Workflow,
                  (Workflow.id == ABTest.workflow_a_id) | (Workflow.id == ABTest.workflow_b_id))
            .where(Workflow.owner_id == user.id)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Get tests with ownership filter
        query = (
            select(ABTest)
            .join(Workflow,
                  (Workflow.id == ABTest.workflow_a_id) | (Workflow.id == ABTest.workflow_b_id))
            .where(Workflow.owner_id == user.id)
            .order_by(ABTest.created_at.desc())
            .distinct()
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        tests = result.scalars().all()

    return ABTestListResponse(
        tests=[
            ABTestResponse(
                id=test.id,
                name=test.name,
                workflow_a_id=test.workflow_a_id,
                workflow_b_id=test.workflow_b_id,
                traffic_split=test.traffic_split,
                metrics=_parse_metrics(test.metrics),
                status=test.status,
                created_at=test.created_at.isoformat(),
                completed_at=test.completed_at.isoformat() if test.completed_at else None,
            )
            for test in tests
        ],
        total=total,
    )


@router.get("/{test_id}", response_model=ABTestDetailResponse)
@require_permission("execution:read")
async def get_ab_test(
    test_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get A/B test with statistics.

    Args:
        test_id: Test ID
        user: Current authenticated user
        db: Database session

    Returns:
        A/B test with statistics

    Raises:
        HTTPException: If test not found or user doesn't own associated workflows
    """
    # Get test
    result = await db.execute(
        select(ABTest).where(ABTest.id == test_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN:
        # Get the workflows to check ownership
        workflows_result = await db.execute(
            select(Workflow).where(
                Workflow.id.in_([test.workflow_a_id, test.workflow_b_id])
            )
        )
        workflows = workflows_result.scalars().all()
        # User must own at least one of the workflows
        if not any(w.owner_id == user.id for w in workflows):
            raise HTTPException(status_code=404, detail="Test not found")

    # Get statistics
    runner = ABTestRunner(db)
    stats = await runner.get_stats(test_id)

    return ABTestDetailResponse(
        id=test.id,
        name=test.name,
        workflow_a_id=test.workflow_a_id,
        workflow_b_id=test.workflow_b_id,
        traffic_split=test.traffic_split,
        metrics=_parse_metrics(test.metrics),
        status=test.status,
        created_at=test.created_at.isoformat(),
        completed_at=test.completed_at.isoformat() if test.completed_at else None,
        stats={
            variant: ABTestStatsResponse(
                variant=s.variant,
                count=s.count,
                success_rate=s.success_rate,
                avg_duration_ms=s.avg_duration_ms,
            )
            for variant, s in stats.items()
        },
    )


@router.post("/{test_id}/start", response_model=ABTestResponse)
@require_permission("execution:write")
async def start_ab_test(
    test_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Start A/B test.

    Args:
        test_id: Test ID
        user: Current authenticated user
        db: Database session

    Returns:
        Updated A/B test

    Raises:
        HTTPException: If test not found, not in draft status, or user doesn't own workflows
    """
    # Get test
    result = await db.execute(
        select(ABTest).where(ABTest.id == test_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN:
        workflows_result = await db.execute(
            select(Workflow).where(
                Workflow.id.in_([test.workflow_a_id, test.workflow_b_id])
            )
        )
        workflows = workflows_result.scalars().all()
        if not any(w.owner_id == user.id for w in workflows):
            raise HTTPException(status_code=404, detail="Test not found")

    if test.status != "draft":
        raise HTTPException(status_code=400, detail="Test must be in draft status to start")

    # Update status
    test.status = "running"
    await db.commit()
    await db.refresh(test)

    return ABTestResponse(
        id=test.id,
        name=test.name,
        workflow_a_id=test.workflow_a_id,
        workflow_b_id=test.workflow_b_id,
        traffic_split=test.traffic_split,
        metrics=_parse_metrics(test.metrics),
        status=test.status,
        created_at=test.created_at.isoformat(),
        completed_at=test.completed_at.isoformat() if test.completed_at else None,
    )


@router.post("/{test_id}/stop", response_model=ABTestResponse)
@require_permission("execution:write")
async def stop_ab_test(
    test_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Stop A/B test.

    Args:
        test_id: Test ID
        user: Current authenticated user
        db: Database session

    Returns:
        Updated A/B test

    Raises:
        HTTPException: If test not found, not running, or user doesn't own workflows
    """
    # Get test
    result = await db.execute(
        select(ABTest).where(ABTest.id == test_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN:
        workflows_result = await db.execute(
            select(Workflow).where(
                Workflow.id.in_([test.workflow_a_id, test.workflow_b_id])
            )
        )
        workflows = workflows_result.scalars().all()
        if not any(w.owner_id == user.id for w in workflows):
            raise HTTPException(status_code=404, detail="Test not found")

    if test.status != "running":
        raise HTTPException(status_code=400, detail="Test must be running to stop")

    # Update status
    test.status = "completed"
    test.completed_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(test)

    return ABTestResponse(
        id=test.id,
        name=test.name,
        workflow_a_id=test.workflow_a_id,
        workflow_b_id=test.workflow_b_id,
        traffic_split=test.traffic_split,
        metrics=_parse_metrics(test.metrics),
        status=test.status,
        created_at=test.created_at.isoformat(),
        completed_at=test.completed_at.isoformat() if test.completed_at else None,
    )


@router.get("/{test_id}/export")
@require_permission("execution:read")
async def export_ab_test(
    test_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Export A/B test results to CSV.

    Args:
        test_id: Test ID
        user: Current authenticated user
        db: Database session

    Returns:
        CSV file response

    Raises:
        HTTPException: If test not found or user doesn't own workflows
    """
    # Verify test exists
    result = await db.execute(
        select(ABTest).where(ABTest.id == test_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN:
        workflows_result = await db.execute(
            select(Workflow).where(
                Workflow.id.in_([test.workflow_a_id, test.workflow_b_id])
            )
        )
        workflows = workflows_result.scalars().all()
        if not any(w.owner_id == user.id for w in workflows):
            raise HTTPException(status_code=404, detail="Test not found")

    # Export to CSV
    runner = ABTestRunner(db)
    csv_content = await runner.export_csv(test_id)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="ab_test_{test_id}.csv"'
        },
    )
