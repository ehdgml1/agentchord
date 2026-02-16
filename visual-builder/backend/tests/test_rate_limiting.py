"""Tests for API rate limiting security fixes.

H6: Token refresh endpoint rate limiting
H7: SSE connection limiting per user
"""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.api import auth, executions
from app.auth import get_current_user
from app.auth.jwt import User, create_access_token
from app.db.database import get_db
from app.core.rate_limiter import limiter
from app.core.rbac import Role


# === Fixtures ===

@pytest.fixture
def test_app():
    """Create minimal FastAPI app for testing."""
    app = FastAPI()

    # Add rate limiter state
    app.state.limiter = limiter

    # Add routers
    app.include_router(auth.router)
    app.include_router(executions.router)

    return app


@pytest.fixture
def mock_user():
    """Create test user."""
    return User(
        id="test-user-123",
        email="test@example.com",
        role=Role.ADMIN,
    )


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def client(test_app, mock_user, mock_db_session):
    """Create test client with auth override."""

    # Override dependencies
    test_app.dependency_overrides[get_current_user] = lambda: mock_user
    test_app.dependency_overrides[get_db] = lambda: mock_db_session

    with TestClient(test_app) as test_client:
        yield test_client

    # Cleanup
    test_app.dependency_overrides.clear()

    # Reset rate limiter state between tests
    limiter.reset()


# === Tests for H6: Token Refresh Rate Limiting ===

def test_refresh_endpoint_has_rate_limit(client, mock_user):
    """Test that refresh endpoint is rate limited (H6).

    The refresh endpoint should limit requests to 5/minute to prevent
    token grinding attacks.
    """
    # Make multiple requests rapidly
    responses = []
    for i in range(7):  # Exceed the 5/minute limit
        resp = client.post("/api/auth/refresh")
        responses.append(resp)

    # First 5 should succeed
    for i in range(5):
        assert responses[i].status_code == 200, f"Request {i+1} should succeed"

    # 6th and 7th should be rate limited
    assert responses[5].status_code == 429, "6th request should be rate limited"
    assert responses[6].status_code == 429, "7th request should be rate limited"


def test_refresh_returns_valid_token(client, mock_user):
    """Test that refresh endpoint returns valid token structure."""
    resp = client.post("/api/auth/refresh")

    assert resp.status_code == 200
    data = resp.json()

    assert "token" in data
    assert "user_id" in data
    assert "email" in data
    assert "role" in data

    assert data["user_id"] == mock_user.id
    assert data["email"] == mock_user.email


# === Tests for H7: SSE Connection Limiting ===

@pytest.mark.asyncio
async def test_sse_connection_limit_per_user():
    """Test that SSE endpoint limits connections per user (H7).

    Each user should be limited to 5 concurrent SSE connections
    to prevent resource exhaustion.
    """
    from app.api.executions import _track_sse_connection, _release_sse_connection, _sse_connections

    # Clear any existing connections
    _sse_connections.clear()

    user_id = "test-user-456"

    # Track 5 connections - should all succeed
    for i in range(5):
        await _track_sse_connection(user_id)
        assert _sse_connections[user_id] == i + 1

    # 6th connection should fail
    with pytest.raises(Exception) as exc_info:
        await _track_sse_connection(user_id)

    assert exc_info.value.status_code == 429
    assert "TOO_MANY_CONNECTIONS" in str(exc_info.value.detail)

    # Release one connection
    _release_sse_connection(user_id)
    assert _sse_connections[user_id] == 4

    # Now should be able to add one more
    await _track_sse_connection(user_id)
    assert _sse_connections[user_id] == 5

    # Cleanup
    for _ in range(5):
        _release_sse_connection(user_id)

    assert user_id not in _sse_connections


@pytest.mark.asyncio
async def test_sse_connection_release():
    """Test that SSE connections are properly released."""
    from app.api.executions import _track_sse_connection, _release_sse_connection, _sse_connections

    # Clear any existing connections
    _sse_connections.clear()

    user_id = "test-user-789"

    # Add one connection
    await _track_sse_connection(user_id)
    assert _sse_connections[user_id] == 1

    # Release it - user should be removed from dict
    _release_sse_connection(user_id)
    assert user_id not in _sse_connections


@pytest.mark.asyncio
async def test_sse_connection_multiple_users():
    """Test that SSE connection limits are per-user."""
    from app.api.executions import _track_sse_connection, _release_sse_connection, _sse_connections

    # Clear any existing connections
    _sse_connections.clear()

    user1 = "user-1"
    user2 = "user-2"

    # Each user can have 5 connections independently
    for i in range(5):
        await _track_sse_connection(user1)
        await _track_sse_connection(user2)

    assert _sse_connections[user1] == 5
    assert _sse_connections[user2] == 5

    # Both should fail their 6th
    with pytest.raises(Exception) as exc1:
        await _track_sse_connection(user1)
    with pytest.raises(Exception) as exc2:
        await _track_sse_connection(user2)

    assert exc1.value.status_code == 429
    assert exc2.value.status_code == 429

    # Cleanup
    for _ in range(5):
        _release_sse_connection(user1)
        _release_sse_connection(user2)


# === Integration Test ===

def test_rate_limiting_integration(client, mock_user, mock_db_session):
    """Integration test: verify both rate limits work together."""
    from app.api.executions import _sse_connections

    # Clear SSE connections
    _sse_connections.clear()

    # Test refresh rate limit
    refresh_responses = []
    for i in range(7):
        resp = client.post("/api/auth/refresh")
        refresh_responses.append(resp)

    # Check refresh rate limit working
    success_count = sum(1 for r in refresh_responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in refresh_responses if r.status_code == 429)

    assert success_count == 5, "Should allow 5 refresh requests"
    assert rate_limited_count == 2, "Should rate limit 2 requests"

    # SSE connection limiting is tested separately since it requires
    # actual execution setup
