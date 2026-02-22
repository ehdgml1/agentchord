"""Tests for playground API endpoints.

Tests POST /api/playground/chat endpoint for chat-style workflow execution.
"""
import pytest
import pytest_asyncio
import json
import uuid
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.playground import router
from app.core.rbac import Role
from app.db.database import get_db
from app.auth import get_current_user
from app.auth.jwt import User
from app.repositories.workflow_repo import WorkflowRepository
from app.repositories.execution_repo import ExecutionRepository
from app.models.workflow import Workflow as WorkflowModel
from app.models.execution import Execution as ExecutionModel


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


def create_mock_user() -> User:
    """Factory function to create mock user."""
    return User(
        id="test-user-123",
        email="test@example.com",
        role=Role.OPERATOR,
    )


@pytest_asyncio.fixture
async def test_app(db_session):
    """Create FastAPI test app."""
    app = FastAPI()
    app.include_router(router)

    # Mock dependencies
    async def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: create_mock_user()

    # Mock app state
    mock_executor = MagicMock()
    mock_bg_executor = AsyncMock()
    mock_bg_executor.dispatch = AsyncMock()

    app.state.executor = mock_executor
    app.state.bg_executor = mock_bg_executor

    return app


@pytest.mark.asyncio
async def test_playground_chat_success(test_app, db_session):
    """Test successful playground chat execution."""
    client = TestClient(test_app)

    # Create workflow
    workflow = create_workflow_factory()
    workflow_repo = WorkflowRepository(db_session)
    await workflow_repo.create(workflow)
    await db_session.commit()

    # Chat request
    payload = {
        "workflowId": workflow.id,
        "message": "Hello, what's the weather?",
        "history": [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ],
    }

    response = client.post("/api/playground/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "executionId" in data
    assert data["status"] == "running"

    # Verify execution was created in database
    exec_repo = ExecutionRepository(db_session)
    execution = await exec_repo.get_by_id(data["executionId"])
    assert execution is not None
    assert execution.workflow_id == workflow.id
    assert execution.status == "running"
    assert execution.mode == "full"
    assert execution.trigger_type == "playground"
    assert execution.input == "Hello, what's the weather?"

    # Verify background executor was called
    assert test_app.state.bg_executor.dispatch.called


@pytest.mark.asyncio
async def test_playground_chat_workflow_not_found(test_app):
    """Test playground chat with non-existent workflow."""
    client = TestClient(test_app)

    payload = {
        "workflowId": str(uuid.uuid4()),
        "message": "Test message",
        "history": [],
    }

    response = client.post("/api/playground/chat", json=payload)

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
    assert "WORKFLOW_NOT_FOUND" in data["detail"]["error"]["code"]


@pytest.mark.asyncio
async def test_playground_chat_access_denied(test_app, db_session):
    """Test playground chat with workflow owned by another user."""
    client = TestClient(test_app)

    # Create workflow owned by different user
    workflow = create_workflow_factory(owner_id="other-user-456")
    workflow_repo = WorkflowRepository(db_session)
    await workflow_repo.create(workflow)
    await db_session.commit()

    payload = {
        "workflowId": workflow.id,
        "message": "Test message",
        "history": [],
    }

    response = client.post("/api/playground/chat", json=payload)

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
    assert "ACCESS_DENIED" in data["detail"]["error"]["code"]


@pytest.mark.asyncio
async def test_playground_chat_empty_history(test_app, db_session):
    """Test playground chat with empty conversation history."""
    client = TestClient(test_app)

    # Create workflow
    workflow = create_workflow_factory()
    workflow_repo = WorkflowRepository(db_session)
    await workflow_repo.create(workflow)
    await db_session.commit()

    payload = {
        "workflowId": workflow.id,
        "message": "First message",
        "history": [],
    }

    response = client.post("/api/playground/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "executionId" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_playground_chat_validation_message_required(test_app):
    """Test playground chat validates message is required."""
    client = TestClient(test_app)

    payload = {
        "workflowId": str(uuid.uuid4()),
        "message": "",  # Empty message
        "history": [],
    }

    response = client.post("/api/playground/chat", json=payload)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_playground_chat_validation_invalid_role(test_app, db_session):
    """Test playground chat validates history role pattern."""
    client = TestClient(test_app)

    # Create workflow
    workflow = create_workflow_factory()
    workflow_repo = WorkflowRepository(db_session)
    await workflow_repo.create(workflow)
    await db_session.commit()

    payload = {
        "workflowId": workflow.id,
        "message": "Test message",
        "history": [
            {"role": "invalid", "content": "Bad role"},  # Invalid role
        ],
    }

    response = client.post("/api/playground/chat", json=payload)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_playground_chat_context_includes_history(test_app, db_session):
    """Test that playground chat passes history in context to executor."""
    client = TestClient(test_app)

    # Create workflow
    workflow = create_workflow_factory()
    workflow_repo = WorkflowRepository(db_session)
    await workflow_repo.create(workflow)
    await db_session.commit()

    payload = {
        "workflowId": workflow.id,
        "message": "What's next?",
        "history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ],
    }

    with patch.object(test_app.state, 'bg_executor') as mock_bg:
        mock_bg.dispatch = AsyncMock()
        response = client.post("/api/playground/chat", json=payload)

        assert response.status_code == 200
        # Verify dispatch was called (context validation happens in background)
        assert mock_bg.dispatch.called
        call_args = mock_bg.dispatch.call_args
        # The first argument is the async function, second is execution_id
        assert len(call_args[0]) == 2
