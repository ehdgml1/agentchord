"""Security tests for IDOR vulnerabilities in webhooks and schedules.

Tests that users cannot access other users' webhooks and schedules.
"""
import pytest
import pytest_asyncio
import json
import uuid
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.api.webhooks import router as webhook_router
from app.api.schedules import router as schedule_router, set_scheduler
from app.core.scheduler import WorkflowScheduler
from app.core.rbac import Role
from app.db.database import get_db
from app.auth import get_current_user
from app.auth.jwt import User
from app.repositories.webhook_repo import WebhookRepository
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.workflow_repo import WorkflowRepository
from app.models.workflow import Workflow as WorkflowModel


# Test users
USER_A_ID = "user-a-123"
USER_B_ID = "user-b-456"


def create_user(user_id: str) -> User:
    """Create a test user."""
    return User(
        id=user_id,
        email=f"user-{user_id}@example.com",
        role=Role.ADMIN,
    )


def create_workflow_for_user(user_id: str, workflow_id: str | None = None) -> WorkflowModel:
    """Create a workflow owned by a specific user."""
    return WorkflowModel(
        id=workflow_id or str(uuid.uuid4()),
        name=f"Workflow for {user_id}",
        description="Test workflow",
        nodes=json.dumps([
            {
                "id": "node-1",
                "type": "agent",
                "data": {"name": "Test Agent", "model": "gpt-4o-mini"},
            }
        ]),
        edges=json.dumps([]),
        status="active",
        owner_id=user_id,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )


class TestWebhookIDOR:
    """Test webhook IDOR vulnerabilities are fixed."""

    @pytest_asyncio.fixture
    async def webhook_app(self, db_session):
        """Create FastAPI app with webhook router."""
        app = FastAPI()
        app.include_router(webhook_router)

        # Override database dependency
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        return app

    @pytest_asyncio.fixture
    async def user_a_workflows(self, db_session):
        """Create workflows for user A."""
        workflow_a = create_workflow_for_user(USER_A_ID, "workflow-a-1")
        db_session.add(workflow_a)
        await db_session.commit()
        await db_session.refresh(workflow_a)
        return {"workflow_a": workflow_a}

    @pytest_asyncio.fixture
    async def user_b_workflows(self, db_session):
        """Create workflows for user B."""
        workflow_b = create_workflow_for_user(USER_B_ID, "workflow-b-1")
        db_session.add(workflow_b)
        await db_session.commit()
        await db_session.refresh(workflow_b)
        return {"workflow_b": workflow_b}

    @pytest_asyncio.fixture
    async def user_a_webhook(self, db_session, user_a_workflows):
        """Create a webhook for user A's workflow."""
        repo = WebhookRepository(db_session)
        webhook = await repo.create(
            workflow_id=user_a_workflows["workflow_a"].id,
            secret="secret-a",
            allowed_ips=None,
            input_mapping=None,
        )
        await db_session.commit()
        return webhook

    @pytest.mark.asyncio
    async def test_user_cannot_list_other_users_webhooks(
        self, webhook_app, db_session, user_a_webhook, user_b_workflows
    ):
        """User B should not see user A's webhooks."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        webhook_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(webhook_app) as client:
            response = client.get("/webhook")
            assert response.status_code == 200
            data = response.json()
            # User B should see 0 webhooks (user A's webhook is filtered out)
            assert data["total"] == 0
            assert len(data["webhooks"]) == 0

    @pytest.mark.asyncio
    async def test_user_can_list_own_webhooks(
        self, webhook_app, db_session, user_a_webhook
    ):
        """User A should see their own webhooks."""
        # Override user dependency to return user A
        def override_get_current_user():
            return create_user(USER_A_ID)

        webhook_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(webhook_app) as client:
            response = client.get("/webhook")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["webhooks"]) == 1
            assert data["webhooks"][0]["id"] == user_a_webhook.id

    @pytest.mark.asyncio
    async def test_user_cannot_get_other_users_webhook(
        self, webhook_app, db_session, user_a_webhook
    ):
        """User B should get 404 when trying to access user A's webhook."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        webhook_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(webhook_app) as client:
            response = client.get(f"/webhook/{user_a_webhook.id}")
            # Should return 404 (not 403) to prevent enumeration
            assert response.status_code == 404
            data = response.json()
            # Check nested error structure
            if "detail" in data:
                assert data["detail"]["error"]["code"] == "NOT_FOUND"
            else:
                assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_user_can_get_own_webhook(
        self, webhook_app, db_session, user_a_webhook
    ):
        """User A should be able to get their own webhook."""
        # Override user dependency to return user A
        def override_get_current_user():
            return create_user(USER_A_ID)

        webhook_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(webhook_app) as client:
            response = client.get(f"/webhook/{user_a_webhook.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == user_a_webhook.id

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_webhook(
        self, webhook_app, db_session, user_a_webhook
    ):
        """User B should not be able to delete user A's webhook."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        webhook_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(webhook_app) as client:
            response = client.delete(f"/webhook/{user_a_webhook.id}")
            # Should return 404 (not 403) to prevent enumeration
            assert response.status_code == 404

        # Verify webhook still exists
        repo = WebhookRepository(db_session)
        webhook = await repo.get_by_id(user_a_webhook.id)
        assert webhook is not None

    @pytest.mark.asyncio
    async def test_user_cannot_create_webhook_for_other_users_workflow(
        self, webhook_app, db_session, user_a_workflows
    ):
        """User B should not be able to create a webhook for user A's workflow."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        webhook_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(webhook_app) as client:
            response = client.post(
                "/webhook",
                json={
                    "workflowId": user_a_workflows["workflow_a"].id,
                    "allowedIps": None,
                    "inputMapping": None,
                },
            )
            # Should return 403 (operation is blocked)
            assert response.status_code == 403
            data = response.json()
            # Check nested error structure
            if "detail" in data:
                assert data["detail"]["error"]["code"] == "ACCESS_DENIED"
            else:
                assert data["error"]["code"] == "ACCESS_DENIED"


class TestScheduleIDOR:
    """Test schedule IDOR vulnerabilities are fixed."""

    @pytest_asyncio.fixture
    async def schedule_app(self, db_session):
        """Create FastAPI app with schedule router."""
        app = FastAPI()
        app.include_router(schedule_router)

        # Override database dependency
        async def override_get_db():
            yield db_session

        # Mock scheduler
        scheduler = MagicMock(spec=WorkflowScheduler)
        scheduler.add_schedule = AsyncMock()
        scheduler.remove_schedule = AsyncMock()
        scheduler.update_schedule = AsyncMock()
        scheduler.enable_schedule = AsyncMock()
        scheduler.disable_schedule = AsyncMock()
        set_scheduler(scheduler)

        app.dependency_overrides[get_db] = override_get_db
        return app

    @pytest_asyncio.fixture
    async def user_a_workflows(self, db_session):
        """Create workflows for user A."""
        workflow_a = create_workflow_for_user(USER_A_ID, "workflow-a-1")
        db_session.add(workflow_a)
        await db_session.commit()
        await db_session.refresh(workflow_a)
        return {"workflow_a": workflow_a}

    @pytest_asyncio.fixture
    async def user_b_workflows(self, db_session):
        """Create workflows for user B."""
        workflow_b = create_workflow_for_user(USER_B_ID, "workflow-b-1")
        db_session.add(workflow_b)
        await db_session.commit()
        await db_session.refresh(workflow_b)
        return {"workflow_b": workflow_b}

    @pytest_asyncio.fixture
    async def user_a_schedule(self, db_session, user_a_workflows):
        """Create a schedule for user A's workflow."""
        repo = ScheduleRepository(db_session)
        schedule = await repo.create(
            workflow_id=user_a_workflows["workflow_a"].id,
            expression="0 9 * * *",
            input_data={"test": "data"},
            timezone="UTC",
        )
        await db_session.commit()
        return schedule

    @pytest.mark.asyncio
    async def test_user_cannot_list_other_users_schedules(
        self, schedule_app, db_session, user_a_schedule, user_b_workflows
    ):
        """User B should not see user A's schedules."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.get("/api/schedules")
            assert response.status_code == 200
            data = response.json()
            # User B should see 0 schedules
            assert data["total"] == 0
            assert len(data["schedules"]) == 0

    @pytest.mark.asyncio
    async def test_user_can_list_own_schedules(
        self, schedule_app, db_session, user_a_schedule
    ):
        """User A should see their own schedules."""
        # Override user dependency to return user A
        def override_get_current_user():
            return create_user(USER_A_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.get("/api/schedules")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["schedules"]) == 1
            assert data["schedules"][0]["id"] == user_a_schedule.id

    @pytest.mark.asyncio
    async def test_user_cannot_get_other_users_schedule(
        self, schedule_app, db_session, user_a_schedule
    ):
        """User B should get 404 when trying to access user A's schedule."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.get(f"/api/schedules/{user_a_schedule.id}")
            # Should return 404 (not 403) to prevent enumeration
            assert response.status_code == 404
            data = response.json()
            # Check nested error structure
            if "detail" in data:
                assert data["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"
            else:
                assert data["error"]["code"] == "SCHEDULE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_user_can_get_own_schedule(
        self, schedule_app, db_session, user_a_schedule
    ):
        """User A should be able to get their own schedule."""
        # Override user dependency to return user A
        def override_get_current_user():
            return create_user(USER_A_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.get(f"/api/schedules/{user_a_schedule.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == user_a_schedule.id

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_schedule(
        self, schedule_app, db_session, user_a_schedule
    ):
        """User B should not be able to update user A's schedule."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.put(
                f"/api/schedules/{user_a_schedule.id}",
                json={"expression": "0 10 * * *"},
            )
            # Should return 404 (not 403) to prevent enumeration
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_schedule(
        self, schedule_app, db_session, user_a_schedule
    ):
        """User B should not be able to delete user A's schedule."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.delete(f"/api/schedules/{user_a_schedule.id}")
            # Should return 404 (not 403) to prevent enumeration
            assert response.status_code == 404

        # Verify schedule still exists
        repo = ScheduleRepository(db_session)
        schedule = await repo.get_by_id(user_a_schedule.id)
        assert schedule is not None

    @pytest.mark.asyncio
    async def test_user_cannot_toggle_other_users_schedule(
        self, schedule_app, db_session, user_a_schedule
    ):
        """User B should not be able to toggle user A's schedule."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.post(f"/api/schedules/{user_a_schedule.id}/toggle")
            # Should return 404 (not 403) to prevent enumeration
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_create_schedule_for_other_users_workflow(
        self, schedule_app, db_session, user_a_workflows
    ):
        """User B should not be able to create a schedule for user A's workflow."""
        # Override user dependency to return user B
        def override_get_current_user():
            return create_user(USER_B_ID)

        schedule_app.dependency_overrides[get_current_user] = override_get_current_user

        with TestClient(schedule_app) as client:
            response = client.post(
                "/api/schedules",
                json={
                    "workflowId": user_a_workflows["workflow_a"].id,
                    "expression": "0 9 * * *",
                    "timezone": "UTC",
                    "input": {},
                },
            )
            # Should return 403 (operation is blocked)
            assert response.status_code == 403
            data = response.json()
            # Check nested error structure
            if "detail" in data:
                assert data["detail"]["error"]["code"] == "ACCESS_DENIED"
            else:
                assert data["error"]["code"] == "ACCESS_DENIED"
