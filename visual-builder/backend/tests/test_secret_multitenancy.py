"""Tests for multi-tenant secrets (M13).

Verifies:
- Users can CRUD their own secrets
- Users CANNOT access another user's secrets
- Admin CAN list all secrets
- Same secret name for different users = no conflict
- Backward compatibility: owner_id defaults to 'system'
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.api.secrets import router as secrets_router
from app.core.rbac import Role
from app.core.secret_store import SecretStore
from app.auth import get_current_user
from app.auth.jwt import User


# Test user IDs
USER_A_ID = "user-a-111"
USER_B_ID = "user-b-222"
ADMIN_ID = "admin-999"


def make_user(user_id: str, role: Role = Role.EDITOR) -> User:
    """Create a test user."""
    return User(id=user_id, email=f"{user_id}@example.com", role=role)


# ── SecretStore unit tests ──────────────────────────────────────────


class TestSecretStoreMultiTenancy:
    """Test SecretStore owner_id isolation at the store level."""

    @pytest.mark.asyncio
    async def test_set_and_get_with_owner(self, secret_store):
        """User can set and get their own secret."""
        await secret_store.set("API_KEY", "val-a", owner_id=USER_A_ID)
        result = await secret_store.get("API_KEY", owner_id=USER_A_ID)
        assert result == "val-a"

    @pytest.mark.asyncio
    async def test_get_wrong_owner_returns_none(self, secret_store):
        """Getting a secret with wrong owner_id returns None."""
        await secret_store.set("API_KEY", "val-a", owner_id=USER_A_ID)
        result = await secret_store.get("API_KEY", owner_id=USER_B_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_no_owner_returns_any(self, secret_store):
        """Getting a secret without owner_id (admin) returns the first match."""
        await secret_store.set("API_KEY", "val-a", owner_id=USER_A_ID)
        result = await secret_store.get("API_KEY")
        assert result == "val-a"

    @pytest.mark.asyncio
    async def test_same_name_different_owners(self, secret_store):
        """Same secret name for different owners = no conflict."""
        await secret_store.set("API_KEY", "val-a", owner_id=USER_A_ID)
        await secret_store.set("API_KEY", "val-b", owner_id=USER_B_ID)

        assert await secret_store.get("API_KEY", owner_id=USER_A_ID) == "val-a"
        assert await secret_store.get("API_KEY", owner_id=USER_B_ID) == "val-b"

    @pytest.mark.asyncio
    async def test_delete_scoped_to_owner(self, secret_store):
        """Delete only removes secret for the specified owner."""
        await secret_store.set("API_KEY", "val-a", owner_id=USER_A_ID)
        await secret_store.set("API_KEY", "val-b", owner_id=USER_B_ID)

        await secret_store.delete("API_KEY", owner_id=USER_A_ID)

        assert await secret_store.get("API_KEY", owner_id=USER_A_ID) is None
        assert await secret_store.get("API_KEY", owner_id=USER_B_ID) == "val-b"

    @pytest.mark.asyncio
    async def test_list_scoped_to_owner(self, secret_store):
        """List only returns secrets for the specified owner."""
        await secret_store.set("KEY_ONE", "v1", owner_id=USER_A_ID)
        await secret_store.set("KEY_TWO", "v2", owner_id=USER_A_ID)
        await secret_store.set("KEY_THREE", "v3", owner_id=USER_B_ID)

        a_list = await secret_store.list(owner_id=USER_A_ID)
        b_list = await secret_store.list(owner_id=USER_B_ID)
        all_list = await secret_store.list()

        assert sorted(a_list) == ["KEY_ONE", "KEY_TWO"]
        assert b_list == ["KEY_THREE"]
        assert sorted(all_list) == ["KEY_ONE", "KEY_THREE", "KEY_TWO"]

    @pytest.mark.asyncio
    async def test_list_with_metadata_scoped(self, secret_store):
        """list_with_metadata filters by owner_id."""
        await secret_store.set("MY_SECRET", "s1", owner_id=USER_A_ID)
        await secret_store.set("OTHER_SECRET", "s2", owner_id=USER_B_ID)

        a_meta = await secret_store.list_with_metadata(owner_id=USER_A_ID)
        b_meta = await secret_store.list_with_metadata(owner_id=USER_B_ID)
        all_meta = await secret_store.list_with_metadata()

        assert len(a_meta) == 1
        assert a_meta[0]["name"] == "MY_SECRET"
        assert len(b_meta) == 1
        assert b_meta[0]["name"] == "OTHER_SECRET"
        assert len(all_meta) == 2

    @pytest.mark.asyncio
    async def test_get_metadata_scoped(self, secret_store):
        """get_metadata filters by owner_id."""
        await secret_store.set("SCOPED_KEY", "val", owner_id=USER_A_ID)

        meta_a = await secret_store.get_metadata("SCOPED_KEY", owner_id=USER_A_ID)
        meta_b = await secret_store.get_metadata("SCOPED_KEY", owner_id=USER_B_ID)

        assert meta_a is not None
        assert meta_a["name"] == "SCOPED_KEY"
        assert meta_b is None

    @pytest.mark.asyncio
    async def test_default_owner_id_is_system(self, secret_store):
        """Default owner_id is 'system' for backward compatibility."""
        await secret_store.set("LEGACY_KEY", "legacy-val")
        result = await secret_store.get("LEGACY_KEY", owner_id="system")
        assert result == "legacy-val"

    @pytest.mark.asyncio
    async def test_upsert_same_owner(self, secret_store):
        """Upsert (ON CONFLICT) works within same owner."""
        await secret_store.set("UPSERT_KEY", "v1", owner_id=USER_A_ID)
        await secret_store.set("UPSERT_KEY", "v2", owner_id=USER_A_ID)
        result = await secret_store.get("UPSERT_KEY", owner_id=USER_A_ID)
        assert result == "v2"

    @pytest.mark.asyncio
    async def test_resolve_uses_any_owner(self, secret_store):
        """resolve() still works (uses get without owner_id filter)."""
        await secret_store.set("RESOLVE_KEY", "resolved-value", owner_id=USER_A_ID)
        result = await secret_store.resolve("Bearer ${RESOLVE_KEY}")
        assert result == "Bearer resolved-value"


# ── API integration tests ───────────────────────────────────────────


class TestSecretsAPIMultiTenancy:
    """Test secrets API endpoints with multi-tenant isolation."""

    @pytest_asyncio.fixture
    async def secrets_app(self, secret_store):
        """Create FastAPI app with secrets router and mock secret_store."""
        app = FastAPI()
        app.include_router(secrets_router)
        app.state.secret_store = secret_store
        return app

    def _client_as(self, app: FastAPI, user: User) -> TestClient:
        """Create TestClient authenticated as a specific user."""
        def override_get_current_user():
            return user

        app.dependency_overrides[get_current_user] = override_get_current_user
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_user_creates_own_secret(self, secrets_app):
        """User can create a secret."""
        user_a = make_user(USER_A_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_a)
        resp = client.post(
            "/api/secrets",
            json={"name": "MY_KEY", "value": "my-val", "description": "test"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "MY_KEY"

    @pytest.mark.asyncio
    async def test_user_lists_only_own_secrets(self, secrets_app, secret_store):
        """Non-admin user only sees own secrets."""
        await secret_store.set("USER_A_KEY", "a-val", owner_id=USER_A_ID)
        await secret_store.set("USER_B_KEY", "b-val", owner_id=USER_B_ID)

        user_a = make_user(USER_A_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_a)
        resp = client.get("/api/secrets")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert "USER_A_KEY" in names
        assert "USER_B_KEY" not in names

    @pytest.mark.asyncio
    async def test_admin_lists_all_secrets(self, secrets_app, secret_store):
        """Admin sees all secrets across all owners."""
        await secret_store.set("USER_A_KEY", "a-val", owner_id=USER_A_ID)
        await secret_store.set("USER_B_KEY", "b-val", owner_id=USER_B_ID)

        admin = make_user(ADMIN_ID, Role.ADMIN)
        client = self._client_as(secrets_app, admin)
        resp = client.get("/api/secrets")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert "USER_A_KEY" in names
        assert "USER_B_KEY" in names

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_secret(self, secrets_app, secret_store):
        """User gets 404 when trying to update another user's secret."""
        await secret_store.set("THEIR_KEY", "their-val", owner_id=USER_A_ID)

        user_b = make_user(USER_B_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_b)
        resp = client.put(
            "/api/secrets/THEIR_KEY",
            json={"value": "hacked-val"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_secret(self, secrets_app, secret_store):
        """User gets 404 when trying to delete another user's secret."""
        await secret_store.set("THEIR_KEY", "their-val", owner_id=USER_A_ID)

        user_b = make_user(USER_B_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_b)
        resp = client.delete("/api/secrets/THEIR_KEY")
        assert resp.status_code == 404

        # Verify secret still exists
        val = await secret_store.get("THEIR_KEY", owner_id=USER_A_ID)
        assert val == "their-val"

    @pytest.mark.asyncio
    async def test_same_name_different_users_no_conflict(self, secrets_app):
        """Two users can have secrets with the same name."""
        user_a = make_user(USER_A_ID, Role.EDITOR)
        user_b = make_user(USER_B_ID, Role.EDITOR)

        client_a = self._client_as(secrets_app, user_a)
        resp_a = client_a.post(
            "/api/secrets",
            json={"name": "SHARED_NAME", "value": "val-a", "description": ""},
        )
        assert resp_a.status_code == 201

        client_b = self._client_as(secrets_app, user_b)
        resp_b = client_b.post(
            "/api/secrets",
            json={"name": "SHARED_NAME", "value": "val-b", "description": ""},
        )
        assert resp_b.status_code == 201

    @pytest.mark.asyncio
    async def test_user_can_update_own_secret(self, secrets_app, secret_store):
        """User can update their own secret."""
        await secret_store.set("MY_KEY", "old-val", owner_id=USER_A_ID)

        user_a = make_user(USER_A_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_a)
        resp = client.put(
            "/api/secrets/MY_KEY",
            json={"value": "new-val"},
        )
        assert resp.status_code == 200

        updated = await secret_store.get("MY_KEY", owner_id=USER_A_ID)
        assert updated == "new-val"

    @pytest.mark.asyncio
    async def test_user_can_delete_own_secret(self, secrets_app, secret_store):
        """User can delete their own secret."""
        await secret_store.set("MY_KEY", "val", owner_id=USER_A_ID)

        user_a = make_user(USER_A_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_a)
        resp = client.delete("/api/secrets/MY_KEY")
        assert resp.status_code == 204

        gone = await secret_store.get("MY_KEY", owner_id=USER_A_ID)
        assert gone is None

    @pytest.mark.asyncio
    async def test_duplicate_secret_409(self, secrets_app, secret_store):
        """Creating a secret that already exists for the same user returns 409."""
        await secret_store.set("DUP_KEY", "val", owner_id=USER_A_ID)

        user_a = make_user(USER_A_ID, Role.EDITOR)
        client = self._client_as(secrets_app, user_a)
        resp = client.post(
            "/api/secrets",
            json={"name": "DUP_KEY", "value": "val2", "description": ""},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_secrets(self, secrets_app):
        """Viewer role lacks workflow:write permission."""
        viewer = make_user("viewer-1", Role.VIEWER)
        client = self._client_as(secrets_app, viewer)
        resp = client.get("/api/secrets")
        assert resp.status_code == 403
