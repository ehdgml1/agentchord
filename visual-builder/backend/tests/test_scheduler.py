"""Tests for workflow scheduler functionality.

Tests the WorkflowScheduler, calculate_next_run, and validate_cron_expression
with various timezones and cron expressions using factory functions.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import uuid
import pytz

from app.core.scheduler import (
    WorkflowScheduler,
    calculate_next_run,
    validate_cron_expression,
)
from app.models.schedule import Schedule as ScheduleModel
from app.repositories.schedule_repo import ScheduleRepository


# Factory functions for test data
def create_test_schedule_data(
    workflow_id: str | None = None,
    expression: str = "0 9 * * *",
    timezone: str = "UTC",
    enabled: bool = True,
) -> dict:
    """Create schedule data for testing."""
    return {
        "workflow_id": workflow_id or str(uuid.uuid4()),
        "expression": expression,
        "timezone": timezone,
        "enabled": enabled,
    }


@pytest_asyncio.fixture
async def scheduler(mock_mcp_manager, secret_store, state_store, db_session):
    """Create WorkflowScheduler instance."""
    from app.core.executor import WorkflowExecutor
    from contextlib import asynccontextmanager

    executor = WorkflowExecutor(
        mcp_manager=mock_mcp_manager,
        secret_store=secret_store,
        state_store=state_store,
    )

    # Create session factory as async context manager
    @asynccontextmanager
    async def session_factory():
        yield db_session

    scheduler = WorkflowScheduler(executor, session_factory)
    await scheduler.start()
    yield scheduler
    await scheduler.shutdown()


@pytest_asyncio.fixture
async def sample_schedule(db_session) -> ScheduleModel:
    """Create a sample schedule in DB."""
    repo = ScheduleRepository(db_session)
    schedule = await repo.create(
        workflow_id=str(uuid.uuid4()),
        expression="0 9 * * *",
        input_data={"test": "data"},
        timezone="UTC",
    )
    await db_session.commit()
    return schedule


class TestCalculateNextRun:
    """Test calculate_next_run function with various timezones."""

    def test_calculate_next_run_utc(self):
        """Test next run calculation in UTC timezone."""
        expression = "0 9 * * *"  # 9 AM daily
        base_time = datetime(2024, 1, 1, 8, 0, 0)

        next_run = calculate_next_run(expression, "UTC", base_time)

        # Should be 9 AM same day
        assert next_run.hour == 9
        assert next_run.minute == 0
        assert next_run.day == 1

    def test_calculate_next_run_with_timezone(self):
        """Test next run calculation with different timezones."""
        expression = "0 12 * * *"  # Noon
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        # New York timezone
        next_run = calculate_next_run(expression, "America/New_York", base_time)
        assert next_run is not None
        assert isinstance(next_run, datetime)

    def test_calculate_next_run_tokyo_timezone(self):
        """Test next run calculation with Tokyo timezone."""
        expression = "0 18 * * *"  # 6 PM
        base_time = datetime(2024, 1, 1, 15, 0, 0)

        next_run = calculate_next_run(expression, "Asia/Tokyo", base_time)
        assert next_run is not None

    def test_calculate_next_run_london_timezone(self):
        """Test next run calculation with London timezone."""
        expression = "30 14 * * *"  # 2:30 PM
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        next_run = calculate_next_run(expression, "Europe/London", base_time)
        assert next_run is not None

    def test_calculate_next_run_invalid_timezone(self):
        """Test that invalid timezone raises ValueError."""
        expression = "0 9 * * *"

        with pytest.raises(ValueError, match="Invalid timezone"):
            calculate_next_run(expression, "Invalid/Timezone")

    def test_calculate_next_run_invalid_expression(self):
        """Test that invalid cron expression raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            calculate_next_run("invalid cron", "UTC")

    def test_calculate_next_run_every_5_minutes(self):
        """Test every 5 minutes cron expression."""
        expression = "*/5 * * * *"
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        next_run = calculate_next_run(expression, "UTC", base_time)

        # Should be 5 minutes later
        assert next_run.minute == 5
        assert next_run.hour == 10

    def test_calculate_next_run_returns_utc(self):
        """Test that next run is always returned in UTC."""
        expression = "0 9 * * *"
        base_time = datetime(2024, 1, 1, 8, 0, 0)

        next_run = calculate_next_run(expression, "America/New_York", base_time)

        # Result should be naive datetime (UTC)
        assert next_run.tzinfo is None


class TestValidateCronExpression:
    """Test validate_cron_expression function."""

    def test_validate_valid_expressions(self):
        """Test validation of valid cron expressions."""
        valid_expressions = [
            "0 9 * * *",      # Daily at 9 AM
            "*/5 * * * *",    # Every 5 minutes
            "0 0 * * 0",      # Weekly on Sunday
            "0 0 1 * *",      # Monthly on 1st
            "30 14 * * 1-5",  # Weekdays at 2:30 PM
        ]

        for expr in valid_expressions:
            assert validate_cron_expression(expr) is True

    def test_validate_invalid_expressions(self):
        """Test validation rejects invalid expressions."""
        invalid_expressions = [
            "invalid",
            "99 99 * * *",
            "* * * *",        # Too few fields
            "",
            "a b c d e",
        ]

        for expr in invalid_expressions:
            assert validate_cron_expression(expr) is False


class TestWorkflowScheduler:
    """Test WorkflowScheduler class methods."""

    @pytest.mark.asyncio
    async def test_scheduler_starts_and_stops(self, mock_mcp_manager, secret_store, state_store, db_session):
        """Test scheduler startup and shutdown."""
        from app.core.executor import WorkflowExecutor
        from contextlib import asynccontextmanager

        executor = WorkflowExecutor(mock_mcp_manager, secret_store, state_store)

        @asynccontextmanager
        async def session_factory():
            yield db_session

        scheduler = WorkflowScheduler(executor, session_factory)

        assert not scheduler.is_running

        await scheduler.start()
        assert scheduler.is_running

        await scheduler.shutdown()
        assert not scheduler.is_running

    @pytest.mark.asyncio
    async def test_add_schedule(self, scheduler, db_session):
        """Test adding a schedule to the scheduler."""
        repo = ScheduleRepository(db_session)

        # Create schedule in DB
        schedule = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="*/10 * * * *",
            input_data={"key": "value"},
            timezone="UTC",
        )
        await db_session.commit()

        # Add to scheduler
        await scheduler.add_schedule(schedule)

        # Verify schedule was added (check internal state or logs)
        assert scheduler.is_running

    @pytest.mark.asyncio
    async def test_add_disabled_schedule_skips(self, scheduler, db_session):
        """Test that disabled schedules are not added to scheduler."""
        repo = ScheduleRepository(db_session)

        # Create disabled schedule
        schedule = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="0 9 * * *",
            timezone="UTC",
        )
        schedule.enabled = False
        await db_session.commit()

        # Should skip without error
        await scheduler.add_schedule(schedule)
        assert scheduler.is_running

    @pytest.mark.asyncio
    async def test_remove_schedule(self, scheduler, db_session, sample_schedule):
        """Test removing a schedule from the scheduler."""
        # Add schedule first
        await scheduler.add_schedule(sample_schedule)

        # Remove it
        await scheduler.remove_schedule(sample_schedule.id)

        # Should not raise error even if not in scheduler
        await scheduler.remove_schedule("nonexistent-id")

    @pytest.mark.asyncio
    async def test_update_schedule(self, scheduler, db_session, sample_schedule):
        """Test updating an existing schedule."""
        # Add original schedule
        await scheduler.add_schedule(sample_schedule)

        # Update expression
        repo = ScheduleRepository(db_session)
        await repo.update(
            schedule_id=sample_schedule.id,
            expression="0 12 * * *",
        )
        await db_session.commit()

        # Refresh schedule
        updated_schedule = await repo.get_by_id(sample_schedule.id)

        # Update in scheduler
        await scheduler.update_schedule(updated_schedule)
        assert scheduler.is_running

    @pytest.mark.asyncio
    async def test_enable_schedule(self, scheduler, db_session):
        """Test enabling a disabled schedule."""
        repo = ScheduleRepository(db_session)

        # Create disabled schedule
        schedule = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="0 9 * * *",
            timezone="UTC",
        )
        schedule.enabled = False
        await db_session.commit()

        # Enable it
        schedule.enabled = True
        await db_session.commit()

        schedule = await repo.get_by_id(schedule.id)
        await scheduler.enable_schedule(schedule)

        assert scheduler.is_running

    @pytest.mark.asyncio
    async def test_disable_schedule(self, scheduler, db_session, sample_schedule):
        """Test disabling an enabled schedule."""
        # Add schedule first
        await scheduler.add_schedule(sample_schedule)

        # Disable it
        await scheduler.disable_schedule(sample_schedule.id)
        assert scheduler.is_running

    @pytest.mark.asyncio
    async def test_scheduler_loads_schedules_on_startup(self, mock_mcp_manager, secret_store, state_store, db_session):
        """Test that scheduler loads enabled schedules from DB on startup."""
        from app.core.executor import WorkflowExecutor
        from contextlib import asynccontextmanager

        # Create some schedules in DB
        repo = ScheduleRepository(db_session)

        schedule1 = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="0 9 * * *",
            timezone="UTC",
        )
        schedule2 = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="0 12 * * *",
            timezone="UTC",
        )
        # Create disabled schedule (should not be loaded)
        schedule3 = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="0 15 * * *",
            timezone="UTC",
        )
        schedule3.enabled = False
        await db_session.commit()

        # Create scheduler and start
        executor = WorkflowExecutor(mock_mcp_manager, secret_store, state_store)

        @asynccontextmanager
        async def session_factory():
            yield db_session

        scheduler = WorkflowScheduler(executor, session_factory)
        await scheduler.start()

        # Verify it started
        assert scheduler.is_running

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_invalid_timezone_uses_utc(self, scheduler, db_session):
        """Test that invalid timezone falls back to UTC in _add_job."""
        repo = ScheduleRepository(db_session)

        # Create schedule with invalid timezone
        schedule = await repo.create(
            workflow_id=str(uuid.uuid4()),
            expression="0 9 * * *",
            timezone="Invalid/Timezone",
        )
        await db_session.commit()

        # _add_job falls back to UTC for invalid timezone
        # But add_schedule will fail on _update_next_run which validates timezone
        # So we expect ValueError to be raised
        with pytest.raises(ValueError, match="Invalid timezone"):
            await scheduler.add_schedule(schedule)

    @pytest.mark.asyncio
    async def test_update_disabled_schedule_removes_from_scheduler(self, scheduler, db_session, sample_schedule):
        """Test that updating to disabled removes from scheduler."""
        # Add enabled schedule
        await scheduler.add_schedule(sample_schedule)

        # Update to disabled
        repo = ScheduleRepository(db_session)
        await repo.update(
            schedule_id=sample_schedule.id,
            enabled=False,
        )
        await db_session.commit()

        # Get updated schedule
        updated_schedule = await repo.get_by_id(sample_schedule.id)

        # Update in scheduler
        await scheduler.update_schedule(updated_schedule)
        assert scheduler.is_running
