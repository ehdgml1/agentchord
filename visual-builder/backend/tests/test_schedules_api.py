"""Tests for schedules API endpoints.

Tests POST, GET, PUT, DELETE operations for /api/schedules endpoints
using TestClient and factory functions (no hardcoded data).
"""
import pytest
import pytest_asyncio
import json
import uuid
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.api.schedules import router, set_scheduler
from app.core.scheduler import WorkflowScheduler
from app.core.rbac import Role
from app.db.database import get_db
from app.auth import get_current_user
from app.auth.jwt import User
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.workflow_repo import WorkflowRepository
from app.models.workflow import Workflow as WorkflowModel


# Factory functions for test data
def create_workflow_factory(
    workflow_id: str | None = None,
    name: str = "Test Workflow",
    owner_id: str | None = "test-user-123",
) -> WorkflowModel:
    """Factory function to create workflow model."""
    return WorkflowModel(
        id=workflow_id or str(uuid.uuid4()),
        name=name,
        description="Test workflow description",
        nodes=json.dumps([
            {
                "id": "node-1",
                "type": "agent",
                "data": {"name": "Test Agent", "model": "gpt-4o-mini"},
            }
        ]),
        edges=json.dumps([]),
        status="active",
        owner_id=owner_id,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )


def create_schedule_payload(
    workflow_id: str | None = None,
    expression: str = "0 9 * * *",
    timezone: str = "UTC",
    input_data: dict | None = None,
) -> dict:
    """Factory function to create schedule creation payload."""
    return {
        "workflow_id": workflow_id or str(uuid.uuid4()),
        "expression": expression,
        "timezone": timezone,
        "input": input_data or {},
    }


def create_mock_user() -> User:
    """Factory function to create mock user."""
    return User(
        id="test-user-123",  # Fixed user ID for test consistency
        email="test@example.com",
        role=Role.ADMIN,
    )


@pytest_asyncio.fixture
async def test_app(db_session):
    """Create FastAPI test app."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return create_mock_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest_asyncio.fixture
async def mock_scheduler():
    """Create mock WorkflowScheduler."""
    scheduler = MagicMock(spec=WorkflowScheduler)
    scheduler.add_schedule = AsyncMock()
    scheduler.remove_schedule = AsyncMock()
    scheduler.update_schedule = AsyncMock()
    scheduler.enable_schedule = AsyncMock()
    scheduler.disable_schedule = AsyncMock()
    return scheduler


@pytest_asyncio.fixture
async def test_client(test_app, mock_scheduler):
    """Create FastAPI TestClient."""
    set_scheduler(mock_scheduler)
    with TestClient(test_app) as client:
        yield client


@pytest_asyncio.fixture
async def sample_workflow(db_session) -> WorkflowModel:
    """Create a sample workflow in DB."""
    workflow = create_workflow_factory()
    db_session.add(workflow)
    await db_session.commit()
    await db_session.refresh(workflow)
    return workflow


class TestCreateSchedule:
    """Test POST /api/schedules endpoint."""

    @pytest.mark.asyncio
    async def test_create_schedule_success(self, test_client, db_session, sample_workflow):
        """Test successful schedule creation."""
        payload = create_schedule_payload(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
            input_data={"key": "value"},
        )

        response = test_client.post("/api/schedules", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["workflowId"] == sample_workflow.id
        assert data["expression"] == "0 9 * * *"
        assert data["timezone"] == "UTC"
        assert data["enabled"] is True
        assert data["input"] == {"key": "value"}
        assert "id" in data
        assert "nextRunAt" in data

    @pytest.mark.asyncio
    async def test_create_schedule_with_timezone(self, test_client, db_session, sample_workflow):
        """Test creating schedule with different timezone."""
        payload = create_schedule_payload(
            workflow_id=sample_workflow.id,
            expression="0 12 * * *",
            timezone="America/New_York",
        )

        response = test_client.post("/api/schedules", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_create_schedule_invalid_cron_expression(self, test_client, db_session, sample_workflow):
        """Test that invalid cron expression returns 400."""
        payload = create_schedule_payload(
            workflow_id=sample_workflow.id,
            expression="invalid cron",
        )

        response = test_client.post("/api/schedules", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INVALID_EXPRESSION"

    @pytest.mark.asyncio
    async def test_create_schedule_invalid_timezone(self, test_client, db_session, sample_workflow):
        """Test that invalid timezone returns 400."""
        payload = create_schedule_payload(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="Invalid/Timezone",
        )

        response = test_client.post("/api/schedules", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INVALID_TIMEZONE"

    @pytest.mark.asyncio
    async def test_create_schedule_workflow_not_found(self, test_client, db_session):
        """Test that non-existent workflow returns 404."""
        payload = create_schedule_payload(
            workflow_id=str(uuid.uuid4()),
            expression="0 9 * * *",
        )

        response = test_client.post("/api/schedules", json=payload)

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "WORKFLOW_NOT_FOUND"


class TestListSchedules:
    """Test GET /api/schedules endpoint."""

    @pytest.mark.asyncio
    async def test_list_schedules_empty(self, test_client, db_session):
        """Test listing schedules when none exist."""
        response = test_client.get("/api/schedules")

        assert response.status_code == 200
        data = response.json()
        assert data["schedules"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_schedules(self, test_client, db_session, sample_workflow):
        """Test listing schedules."""
        # Create schedules using repository
        repo = ScheduleRepository(db_session)

        schedule1 = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            input_data={"test": "data1"},
            timezone="UTC",
        )
        schedule2 = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 12 * * *",
            input_data={"test": "data2"},
            timezone="UTC",
        )
        await db_session.commit()

        response = test_client.get("/api/schedules")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["schedules"]) == 2

    @pytest.mark.asyncio
    async def test_list_schedules_filter_by_workflow(self, test_client, db_session, sample_workflow):
        """Test filtering schedules by workflow_id."""
        # Create workflow 2
        workflow2 = create_workflow_factory(name="Workflow 2")
        db_session.add(workflow2)
        await db_session.commit()

        # Create schedules for both workflows
        repo = ScheduleRepository(db_session)

        schedule1 = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
        )
        schedule2 = await repo.create(
            workflow_id=workflow2.id,
            expression="0 12 * * *",
        )
        await db_session.commit()

        # Filter by workflow1
        response = test_client.get(f"/api/schedules?workflow_id={sample_workflow.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["schedules"][0]["workflowId"] == sample_workflow.id


class TestGetSchedule:
    """Test GET /api/schedules/{schedule_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_schedule_success(self, test_client, db_session, sample_workflow):
        """Test getting schedule by ID."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            input_data={"key": "value"},
            timezone="UTC",
        )
        await db_session.commit()

        response = test_client.get(f"/api/schedules/{schedule.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == schedule.id
        assert data["workflowId"] == sample_workflow.id

    @pytest.mark.asyncio
    async def test_get_schedule_not_found(self, test_client, db_session):
        """Test getting non-existent schedule returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/schedules/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"


class TestUpdateSchedule:
    """Test PUT /api/schedules/{schedule_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_schedule_expression(self, test_client, db_session, sample_workflow):
        """Test updating schedule expression."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        await db_session.commit()

        update_payload = {
            "expression": "0 12 * * *",
        }

        response = test_client.put(f"/api/schedules/{schedule.id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["expression"] == "0 12 * * *"

    @pytest.mark.asyncio
    async def test_update_schedule_timezone(self, test_client, db_session, sample_workflow):
        """Test updating schedule timezone."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        await db_session.commit()

        update_payload = {
            "timezone": "America/New_York",
        }

        response = test_client.put(f"/api/schedules/{schedule.id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_update_schedule_input(self, test_client, db_session, sample_workflow):
        """Test updating schedule input data."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            input_data={"old": "data"},
            timezone="UTC",
        )
        await db_session.commit()

        update_payload = {
            "input": {"new": "data", "count": 42},
        }

        response = test_client.put(f"/api/schedules/{schedule.id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["input"] == {"new": "data", "count": 42}

    @pytest.mark.asyncio
    async def test_update_schedule_enabled(self, test_client, db_session, sample_workflow):
        """Test updating schedule enabled status."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        await db_session.commit()

        update_payload = {
            "enabled": False,
        }

        response = test_client.put(f"/api/schedules/{schedule.id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_schedule_invalid_expression(self, test_client, db_session, sample_workflow):
        """Test that invalid expression in update returns 400."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        await db_session.commit()

        update_payload = {
            "expression": "invalid cron",
        }

        response = test_client.put(f"/api/schedules/{schedule.id}", json=update_payload)

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_EXPRESSION"

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self, test_client, db_session):
        """Test updating non-existent schedule returns 404."""
        fake_id = str(uuid.uuid4())
        update_payload = {
            "expression": "0 12 * * *",
        }

        response = test_client.put(f"/api/schedules/{fake_id}", json=update_payload)

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"


class TestDeleteSchedule:
    """Test DELETE /api/schedules/{schedule_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_schedule_success(self, test_client, db_session, sample_workflow):
        """Test deleting a schedule."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        await db_session.commit()

        response = test_client.delete(f"/api/schedules/{schedule.id}")

        assert response.status_code == 204

        # Verify deleted
        deleted_schedule = await repo.get_by_id(schedule.id)
        assert deleted_schedule is None

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self, test_client, db_session):
        """Test deleting non-existent schedule returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.delete(f"/api/schedules/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"


class TestToggleSchedule:
    """Test POST /api/schedules/{schedule_id}/toggle endpoint."""

    @pytest.mark.asyncio
    async def test_toggle_schedule_disable(self, test_client, db_session, sample_workflow):
        """Test toggling schedule from enabled to disabled."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        # Ensure enabled
        schedule.enabled = True
        await db_session.commit()

        response = test_client.post(f"/api/schedules/{schedule.id}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_schedule_enable(self, test_client, db_session, sample_workflow):
        """Test toggling schedule from disabled to enabled."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=sample_workflow.id,
            expression="0 9 * * *",
            timezone="UTC",
        )
        # Disable it first
        schedule.enabled = False
        await db_session.commit()

        response = test_client.post(f"/api/schedules/{schedule.id}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        # When enabling, next_run_at should be calculated
        assert data["nextRunAt"] is not None

    @pytest.mark.asyncio
    async def test_toggle_schedule_not_found(self, test_client, db_session):
        """Test toggling non-existent schedule returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.post(f"/api/schedules/{fake_id}/toggle")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"
