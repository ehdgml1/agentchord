"""Workflow scheduler with APScheduler integration.

Phase -1 Implementation:
- AsyncIOScheduler with timezone support
- Cron schedule management
- Load schedules from DB on startup
- Calculate and update next_run_at
- Execute workflows via WorkflowExecutor
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
import pytz

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.executor import WorkflowExecutor
    from app.models.schedule import Schedule

logger = logging.getLogger(__name__)


def calculate_next_run(
    expression: str,
    timezone: str = "UTC",
    base_time: datetime | None = None,
) -> datetime:
    """Calculate next run time from cron expression.

    Args:
        expression: Cron expression (5 or 6 fields).
        timezone: Timezone string (e.g., 'America/New_York').
        base_time: Base time for calculation (default: now).

    Returns:
        Next run datetime in UTC.

    Raises:
        ValueError: If expression or timezone is invalid.
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as e:
        raise ValueError(f"Invalid timezone: {timezone}") from e

    if base_time is None:
        base_time = datetime.now(tz)
    elif base_time.tzinfo is None:
        base_time = tz.localize(base_time)

    try:
        cron = croniter(expression, base_time)
        next_run = cron.get_next(datetime)
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid cron expression: {expression}") from e

    # Convert to UTC for storage
    return next_run.astimezone(pytz.UTC).replace(tzinfo=None)


def validate_cron_expression(expression: str) -> bool:
    """Validate cron expression syntax.

    Args:
        expression: Cron expression to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        croniter(expression)
        return True
    except (ValueError, KeyError):
        return False


class WorkflowScheduler:
    """Manages scheduled workflow executions.

    Integrates APScheduler with WorkflowExecutor to run workflows
    on cron schedules. Supports timezone-aware scheduling.

    Example:
        scheduler = WorkflowScheduler(executor, session_factory)
        await scheduler.start()
        await scheduler.add_schedule(schedule)
    """

    def __init__(
        self,
        executor: WorkflowExecutor,
        session_factory: Any,
    ) -> None:
        """Initialize scheduler.

        Args:
            executor: WorkflowExecutor for running workflows.
            session_factory: Async session factory for DB access.
        """
        self._executor = executor
        self._session_factory = session_factory
        self._scheduler = AsyncIOScheduler()
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running and self._scheduler.running

    async def start(self) -> None:
        """Start the scheduler and load existing schedules."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._scheduler.start()
        self._running = True
        logger.info("Scheduler started")

        await self._load_schedules_from_db()

    async def shutdown(self) -> None:
        """Shutdown the scheduler gracefully."""
        if not self._running:
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Scheduler shutdown complete")

    async def _load_schedules_from_db(self) -> None:
        """Load all enabled schedules from database on startup."""
        from app.repositories.schedule_repo import ScheduleRepository

        async with self._session_factory() as session:
            repo = ScheduleRepository(session)
            schedules = await repo.list_all_enabled()

            for schedule in schedules:
                try:
                    await self._add_job(schedule)
                    logger.info(f"Loaded schedule {schedule.id}")
                except Exception as e:
                    logger.error(f"Failed to load schedule {schedule.id}: {e}")

    async def add_schedule(self, schedule: Schedule) -> None:
        """Add a new schedule to the scheduler.

        Args:
            schedule: Schedule entity to add.
        """
        if not schedule.enabled:
            logger.debug(f"Skipping disabled schedule {schedule.id}")
            return

        await self._add_job(schedule)
        await self._update_next_run(schedule)
        logger.info(f"Added schedule {schedule.id}: {schedule.expression}")

    async def _add_job(self, schedule: Schedule) -> None:
        """Add APScheduler job for schedule.

        Args:
            schedule: Schedule entity.
        """
        try:
            tz = pytz.timezone(schedule.timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
            logger.warning(f"Invalid timezone {schedule.timezone}, using UTC")

        trigger = CronTrigger.from_crontab(
            schedule.expression,
            timezone=tz,
        )

        self._scheduler.add_job(
            self._execute_scheduled_workflow,
            trigger=trigger,
            id=schedule.id,
            args=[schedule.id],
            replace_existing=True,
            misfire_grace_time=60,
        )

    async def remove_schedule(self, schedule_id: str) -> None:
        """Remove a schedule from the scheduler.

        Args:
            schedule_id: ID of schedule to remove.
        """
        try:
            self._scheduler.remove_job(schedule_id)
            logger.info(f"Removed schedule {schedule_id}")
        except Exception:
            logger.debug(f"Schedule {schedule_id} not found in scheduler")

    async def update_schedule(self, schedule: Schedule) -> None:
        """Update an existing schedule.

        Args:
            schedule: Updated schedule entity.
        """
        await self.remove_schedule(schedule.id)

        if schedule.enabled:
            await self._add_job(schedule)
            await self._update_next_run(schedule)
            logger.info(f"Updated schedule {schedule.id}")

    async def enable_schedule(self, schedule: Schedule) -> None:
        """Enable a disabled schedule.

        Args:
            schedule: Schedule to enable.
        """
        await self._add_job(schedule)
        await self._update_next_run(schedule)
        logger.info(f"Enabled schedule {schedule.id}")

    async def disable_schedule(self, schedule_id: str) -> None:
        """Disable a schedule.

        Args:
            schedule_id: ID of schedule to disable.
        """
        await self.remove_schedule(schedule_id)
        logger.info(f"Disabled schedule {schedule_id}")

    async def _execute_scheduled_workflow(self, schedule_id: str) -> None:
        """Execute a scheduled workflow.

        Called by APScheduler when a job triggers.

        Args:
            schedule_id: ID of the triggered schedule.
        """
        from app.repositories.schedule_repo import ScheduleRepository
        from app.repositories.workflow_repo import WorkflowRepository
        from app.core.executor import Workflow, WorkflowNode, WorkflowEdge

        logger.info(f"Executing scheduled workflow for {schedule_id}")

        async with self._session_factory() as session:
            schedule_repo = ScheduleRepository(session)
            workflow_repo = WorkflowRepository(session)

            schedule = await schedule_repo.get_by_id(schedule_id)
            if not schedule or not schedule.enabled:
                logger.warning(f"Schedule {schedule_id} not found or disabled")
                return

            workflow_model = await workflow_repo.get_by_id(schedule.workflow_id)
            if not workflow_model:
                logger.error(f"Workflow {schedule.workflow_id} not found")
                return

            # Parse workflow data
            nodes_data = json.loads(workflow_model.nodes)
            edges_data = json.loads(workflow_model.edges)

            workflow = Workflow(
                id=workflow_model.id,
                name=workflow_model.name,
                nodes=[WorkflowNode(**n) for n in nodes_data],
                edges=[WorkflowEdge(**e) for e in edges_data],
                description=workflow_model.description,
            )

            # Parse schedule input
            input_data = json.loads(schedule.input)
            input_str = json.dumps(input_data)

            # Update last run time
            now = datetime.now(UTC)
            await schedule_repo.update_last_run(schedule_id, now)
            await session.commit()

            # Execute workflow
            try:
                execution = await self._executor.run(
                    workflow=workflow,
                    input=input_str,
                    trigger_type="cron",
                    trigger_id=schedule_id,
                )
                logger.info(
                    f"Scheduled execution {execution.id} "
                    f"completed: {execution.status}"
                )
            except Exception as e:
                logger.error(f"Scheduled execution failed: {e}")

            # Update next run time
            await self._update_next_run_by_id(schedule_id)

    async def _update_next_run(self, schedule: Schedule) -> None:
        """Update next_run_at in database.

        Args:
            schedule: Schedule entity.
        """
        from app.repositories.schedule_repo import ScheduleRepository

        next_run = calculate_next_run(schedule.expression, schedule.timezone)

        async with self._session_factory() as session:
            repo = ScheduleRepository(session)
            await repo.update_next_run(schedule.id, next_run)
            await session.commit()

    async def _update_next_run_by_id(self, schedule_id: str) -> None:
        """Update next_run_at by schedule ID.

        Args:
            schedule_id: Schedule ID.
        """
        from app.repositories.schedule_repo import ScheduleRepository

        async with self._session_factory() as session:
            repo = ScheduleRepository(session)
            schedule = await repo.get_by_id(schedule_id)

            if schedule and schedule.enabled:
                next_run = calculate_next_run(
                    schedule.expression,
                    schedule.timezone,
                )
                await repo.update_next_run(schedule_id, next_run)
                await session.commit()
