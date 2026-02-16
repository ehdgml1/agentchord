"""Tests for RBAC system."""
import pytest
from app.core.rbac import Role, has_permission, require_permission, ROLE_PERMISSIONS


class TestHasPermission:
    """Tests for has_permission function."""

    def test_admin_has_all_permissions(self):
        """Admin should have all permissions."""
        assert has_permission(Role.ADMIN, "anything") is True
        assert has_permission(Role.ADMIN, "workflow:delete") is True
        assert has_permission(Role.ADMIN, "user:manage") is True
        assert has_permission(Role.ADMIN, "system:configure") is True

    def test_viewer_can_only_read(self):
        """Viewer should only have read permissions."""
        assert has_permission(Role.VIEWER, "workflow:read") is True
        assert has_permission(Role.VIEWER, "execution:read") is True
        assert has_permission(Role.VIEWER, "workflow:write") is False
        assert has_permission(Role.VIEWER, "execution:write") is False
        assert has_permission(Role.VIEWER, "schedule:write") is False

    def test_editor_can_write_workflows(self):
        """Editor should be able to write workflows but not manage schedules."""
        assert has_permission(Role.EDITOR, "workflow:read") is True
        assert has_permission(Role.EDITOR, "workflow:write") is True
        assert has_permission(Role.EDITOR, "execution:read") is True
        assert has_permission(Role.EDITOR, "schedule:write") is False
        assert has_permission(Role.EDITOR, "user:manage") is False

    def test_operator_can_manage_schedules(self):
        """Operator should be able to manage schedules and execute workflows."""
        assert has_permission(Role.OPERATOR, "workflow:read") is True
        assert has_permission(Role.OPERATOR, "workflow:write") is True
        assert has_permission(Role.OPERATOR, "execution:read") is True
        assert has_permission(Role.OPERATOR, "execution:write") is True
        assert has_permission(Role.OPERATOR, "schedule:write") is True
        assert has_permission(Role.OPERATOR, "user:manage") is False

    def test_nonexistent_role_has_no_permissions(self):
        """Unknown roles should have no permissions."""
        # Create a mock role that's not in ROLE_PERMISSIONS
        class MockRole:
            pass

        mock_role = MockRole()
        assert has_permission(mock_role, "workflow:read") is False


class TestRequirePermission:
    """Tests for require_permission decorator."""

    @pytest.mark.asyncio
    async def test_decorator_allows_with_permission(self):
        """Decorator should allow access when user has permission."""
        @require_permission("workflow:read")
        async def test_endpoint(user=None):
            return {"status": "success"}

        # Create mock user with VIEWER role
        class MockUser:
            role = Role.VIEWER

        result = await test_endpoint(user=MockUser())
        assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_decorator_denies_without_permission(self):
        """Decorator should deny access when user lacks permission."""
        from fastapi import HTTPException

        @require_permission("workflow:write")
        async def test_endpoint(user=None):
            return {"status": "success"}

        # Create mock user with VIEWER role (no write permission)
        class MockUser:
            role = Role.VIEWER

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(user=MockUser())

        assert exc_info.value.status_code == 403
        assert "Permission denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_decorator_allows_admin_all_permissions(self):
        """Decorator should allow admin access to any permission."""
        @require_permission("super:secret:permission")
        async def test_endpoint(user=None):
            return {"status": "success"}

        # Create mock user with ADMIN role
        class MockUser:
            role = Role.ADMIN

        result = await test_endpoint(user=MockUser())
        assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_decorator_rejects_without_user(self):
        """Decorator should reject access when no user is provided (fail-closed)."""
        from fastapi import HTTPException

        @require_permission("workflow:read")
        async def test_endpoint(user=None):
            return {"status": "success"}

        # Call without user argument - should raise 401 (fail-closed)
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()
        assert exc_info.value.status_code == 401


class TestRolePermissions:
    """Tests for role permission mappings."""

    def test_all_roles_have_permissions(self):
        """All roles should have permission definitions."""
        for role in Role:
            assert role in ROLE_PERMISSIONS
            assert isinstance(ROLE_PERMISSIONS[role], list)

    def test_admin_has_wildcard(self):
        """Admin should have wildcard permission."""
        assert "*" in ROLE_PERMISSIONS[Role.ADMIN]

    def test_viewer_permissions_subset_of_editor(self):
        """Viewer permissions should be subset of editor permissions."""
        viewer_perms = set(ROLE_PERMISSIONS[Role.VIEWER])
        editor_perms = set(ROLE_PERMISSIONS[Role.EDITOR])
        assert viewer_perms.issubset(editor_perms)

    def test_editor_permissions_subset_of_operator(self):
        """Editor permissions should be subset of operator permissions."""
        editor_perms = set(ROLE_PERMISSIONS[Role.EDITOR])
        operator_perms = set(ROLE_PERMISSIONS[Role.OPERATOR])
        assert editor_perms.issubset(operator_perms)
