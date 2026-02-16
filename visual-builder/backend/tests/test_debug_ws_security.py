"""Security tests for debug WebSocket endpoint (IDOR protection).

Tests for Issue C5: Debug WebSocket Missing Ownership Check
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from app.api.debug_ws import _run_debug_workflow


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock(spec=WebSocket)
    ws.client_state = WebSocketState.CONNECTED
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_session():
    """Create a mock DebugSession."""
    from app.core.debug_executor import DebugSession
    return DebugSession()


@pytest.fixture
def mock_workflow():
    """Create a mock workflow with owner."""
    workflow = MagicMock()
    workflow.id = "workflow-123"
    workflow.name = "Test Workflow"
    workflow.owner_id = "user-456"
    workflow.nodes = json.dumps([{"id": "node1", "type": "input"}])
    workflow.edges = json.dumps([])
    return workflow


def _make_session_mock(workflow):
    """Create a proper async session factory mock that returns workflow."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = workflow
    mock_db.execute.return_value = mock_result

    @asynccontextmanager
    async def fake_session():
        yield mock_db

    return fake_session


@pytest.mark.asyncio
async def test_owner_can_debug_workflow(mock_websocket, mock_session, mock_workflow):
    """Test that workflow owner can debug their workflow."""
    user_payload = {
        "sub": "user-456",  # Same as workflow.owner_id
        "role": "user"
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(mock_workflow)):
        with patch("app.api.debug_ws.DebugExecutor") as mock_executor_cls:
            mock_executor = AsyncMock()
            mock_executor.run_debug.return_value = AsyncMock()
            mock_executor.run_debug.return_value.__aiter__ = MagicMock(return_value=iter([]))
            mock_executor_cls.return_value = mock_executor

            await _run_debug_workflow(
                mock_websocket,
                mock_session,
                "workflow-123",
                "test input",
                user_payload
            )

            # Verify no unauthorized close
            mock_websocket.close.assert_not_called()


@pytest.mark.asyncio
async def test_non_owner_cannot_debug_workflow(mock_websocket, mock_session, mock_workflow):
    """Test that non-owner cannot debug another user's workflow (IDOR protection)."""
    user_payload = {
        "sub": "user-999",  # Different from workflow.owner_id
        "role": "user"
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(mock_workflow)):
        await _run_debug_workflow(
            mock_websocket,
            mock_session,
            "workflow-123",
            "test input",
            user_payload
        )

        # Verify unauthorized close
        mock_websocket.close.assert_called_once_with(
            code=4003,
            reason="Not authorized to debug this workflow"
        )


@pytest.mark.asyncio
async def test_admin_can_debug_any_workflow(mock_websocket, mock_session, mock_workflow):
    """Test that admin users can debug any workflow."""
    user_payload = {
        "sub": "admin-999",  # Different from workflow.owner_id
        "role": "admin"      # Admin role bypasses ownership check
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(mock_workflow)):
        with patch("app.api.debug_ws.DebugExecutor") as mock_executor_cls:
            mock_executor = AsyncMock()
            mock_executor.run_debug.return_value = AsyncMock()
            mock_executor.run_debug.return_value.__aiter__ = MagicMock(return_value=iter([]))
            mock_executor_cls.return_value = mock_executor

            await _run_debug_workflow(
                mock_websocket,
                mock_session,
                "workflow-123",
                "test input",
                user_payload
            )

            mock_websocket.close.assert_not_called()


@pytest.mark.asyncio
async def test_legacy_workflow_without_owner(mock_websocket, mock_session, mock_workflow):
    """Test that legacy workflows (owner_id = None) are accessible."""
    mock_workflow.owner_id = None  # Legacy workflow

    user_payload = {
        "sub": "user-999",
        "role": "user"
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(mock_workflow)):
        with patch("app.api.debug_ws.DebugExecutor") as mock_executor_cls:
            mock_executor = AsyncMock()
            mock_executor.run_debug.return_value = AsyncMock()
            mock_executor.run_debug.return_value.__aiter__ = MagicMock(return_value=iter([]))
            mock_executor_cls.return_value = mock_executor

            await _run_debug_workflow(
                mock_websocket,
                mock_session,
                "workflow-123",
                "test input",
                user_payload
            )

            mock_websocket.close.assert_not_called()


@pytest.mark.asyncio
async def test_workflow_not_found(mock_websocket, mock_session):
    """Test that non-existent workflows return error."""
    user_payload = {
        "sub": "user-456",
        "role": "user"
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(None)):
        await _run_debug_workflow(
            mock_websocket,
            mock_session,
            "nonexistent-123",
            "test input",
            user_payload
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert "not found" in call_args["data"]["message"].lower()
        mock_websocket.close.assert_not_called()


@pytest.mark.asyncio
async def test_user_payload_missing_sub(mock_websocket, mock_session, mock_workflow):
    """Test graceful handling when user_payload lacks 'sub' field."""
    user_payload = {
        "role": "user"
        # Missing "sub"
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(mock_workflow)):
        await _run_debug_workflow(
            mock_websocket,
            mock_session,
            "workflow-123",
            "test input",
            user_payload
        )

        mock_websocket.close.assert_called_once_with(
            code=4003,
            reason="Not authorized to debug this workflow"
        )


@pytest.mark.asyncio
async def test_user_payload_missing_role(mock_websocket, mock_session, mock_workflow):
    """Test graceful handling when user_payload lacks 'role' field."""
    user_payload = {
        "sub": "user-999"  # Different from workflow.owner_id
        # Missing "role"
    }

    with patch("app.db.database.AsyncSessionLocal", _make_session_mock(mock_workflow)):
        await _run_debug_workflow(
            mock_websocket,
            mock_session,
            "workflow-123",
            "test input",
            user_payload
        )

        mock_websocket.close.assert_called_once_with(
            code=4003,
            reason="Not authorized to debug this workflow"
        )
