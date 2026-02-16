"""Schedule repository implementation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule


class ScheduleRepository:
    """Schedule repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session.
        """
        self.session = session

    async def create(
        self,
        workflow_id: str,
        expression: str,
        input_data: dict[str, Any] | None = None,
        timezone: str = "UTC",
    ) -> Schedule:
        """Create a new schedule.

        Args:
            workflow_id: ID of workflow to schedule.
            expression: Cron expression.
            input_data: Input to pass to workflow.
            timezone: Schedule timezone.

        Returns:
            Created schedule entity.
        """
        schedule = Schedule(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            type="cron",
            expression=expression,
            input=json.dumps(input_data or {}),
            timezone=timezone,
            enabled=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def get_by_id(self, schedule_id: str) -> Schedule | None:
        """Get schedule by ID.

        Args:
            schedule_id: Schedule ID.

        Returns:
            Schedule entity or None if not found.
        """
        stmt = select(Schedule).where(Schedule.id == schedule_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workflow(self, workflow_id: str) -> list[Schedule]:
        """List all schedules for a workflow.

        Args:
            workflow_id: Workflow ID.

        Returns:
            List of schedules.
        """
        stmt = (
            select(Schedule)
            .where(Schedule.workflow_id == workflow_id)
            .order_by(Schedule.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_enabled(self) -> list[Schedule]:
        """List all enabled schedules.

        Used for loading schedules on startup.

        Returns:
            List of enabled schedules.
        """
        stmt = (
            select(Schedule)
            .where(Schedule.enabled == True)  # noqa: E712
            .order_by(Schedule.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        schedule_id: str,
        expression: str | None = None,
        input_data: dict[str, Any] | None = None,
        timezone: str | None = None,
        enabled: bool | None = None,
    ) -> Schedule | None:
        """Update schedule fields.

        Args:
            schedule_id: Schedule ID.
            expression: New cron expression.
            input_data: New input data.
            timezone: New timezone.
            enabled: New enabled status.

        Returns:
            Updated schedule or None if not found.
        """
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None

        if expression is not None:
            schedule.expression = expression
        if input_data is not None:
            schedule.input = json.dumps(input_data)
        if timezone is not None:
            schedule.timezone = timezone
        if enabled is not None:
            schedule.enabled = enabled

        await self.session.flush()
        return schedule

    async def delete(self, schedule_id: str) -> bool:
        """Delete a schedule.

        Args:
            schedule_id: Schedule ID.

        Returns:
            True if deleted, False if not found.
        """
        stmt = delete(Schedule).where(Schedule.id == schedule_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def update_last_run(
        self,
        schedule_id: str,
        timestamp: datetime,
    ) -> None:
        """Update last run timestamp.

        Args:
            schedule_id: Schedule ID.
            timestamp: Execution timestamp.
        """
        stmt = (
            update(Schedule)
            .where(Schedule.id == schedule_id)
            .values(last_run_at=timestamp)
        )
        await self.session.execute(stmt)

    async def update_next_run(
        self,
        schedule_id: str,
        timestamp: datetime | None,
    ) -> None:
        """Update next run timestamp.

        Args:
            schedule_id: Schedule ID.
            timestamp: Next run timestamp.
        """
        stmt = (
            update(Schedule)
            .where(Schedule.id == schedule_id)
            .values(next_run_at=timestamp)
        )
        await self.session.execute(stmt)
