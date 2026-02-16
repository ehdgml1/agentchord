"""Tests for version store."""
import pytest
import pytest_asyncio
import json
import uuid
from datetime import datetime

from app.core.version_store import WorkflowVersionStore
from app.models.version import WorkflowVersion


# Factory functions for test data
def create_workflow_id() -> str:
    """Factory function to create workflow ID."""
    return str(uuid.uuid4())


def create_workflow_data(
    workflow_id: str | None = None,
    name: str = "Test Workflow",
) -> dict:
    """Factory function to create workflow data."""
    return {
        "id": workflow_id or create_workflow_id(),
        "name": name,
        "description": "Test workflow description",
        "nodes": [
            {
                "id": "node-1",
                "type": "agent",
                "data": {"name": "Agent 1", "role": "Process"},
            },
            {
                "id": "node-2",
                "type": "agent",
                "data": {"name": "Agent 2", "role": "Finalize"},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "node-1", "target": "node-2"},
        ],
        "status": "active",
    }


@pytest_asyncio.fixture
async def version_store(db_session):
    """Create version store with database session."""
    return WorkflowVersionStore(db_session)


class TestSaveVersion:
    """Test WorkflowVersionStore.save_version method."""

    @pytest.mark.asyncio
    async def test_save_version_success(self, version_store, db_session):
        """Test saving workflow version successfully."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)
        message = "Initial version"

        # Save version
        version_id = await version_store.save_version(
            workflow_id, data, message
        )

        # Verify version was created
        assert version_id is not None
        assert isinstance(version_id, str)

        # Verify version can be retrieved
        version = await version_store.get_version(version_id)
        assert version is not None
        assert version["workflow_id"] == workflow_id
        assert version["version_number"] == 1
        assert version["message"] == message

    @pytest.mark.asyncio
    async def test_save_version_increments_version_number(
        self, version_store, db_session
    ):
        """Test version numbers increment correctly."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        # Save first version
        version_id_1 = await version_store.save_version(
            workflow_id, data, "Version 1"
        )
        version_1 = await version_store.get_version(version_id_1)
        assert version_1["version_number"] == 1

        # Save second version
        version_id_2 = await version_store.save_version(
            workflow_id, data, "Version 2"
        )
        version_2 = await version_store.get_version(version_id_2)
        assert version_2["version_number"] == 2

        # Save third version
        version_id_3 = await version_store.save_version(
            workflow_id, data, "Version 3"
        )
        version_3 = await version_store.get_version(version_id_3)
        assert version_3["version_number"] == 3

    @pytest.mark.asyncio
    async def test_save_version_default_message(self, version_store, db_session):
        """Test default version message is generated."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        # Save without message
        version_id = await version_store.save_version(workflow_id, data)

        version = await version_store.get_version(version_id)
        assert version["message"] == "Version 1"

    @pytest.mark.asyncio
    async def test_save_version_preserves_data(self, version_store, db_session):
        """Test version data is preserved correctly."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id, name="My Workflow")

        # Save version
        version_id = await version_store.save_version(
            workflow_id, data, "Test version"
        )

        # Retrieve and verify data
        version = await version_store.get_version(version_id)
        assert version["data"]["name"] == "My Workflow"
        assert version["data"]["description"] == "Test workflow description"
        assert len(version["data"]["nodes"]) == 2
        assert len(version["data"]["edges"]) == 1

    @pytest.mark.asyncio
    async def test_save_version_multiple_workflows(self, version_store, db_session):
        """Test saving versions for multiple workflows."""
        workflow_id_1 = create_workflow_id()
        workflow_id_2 = create_workflow_id()

        data_1 = create_workflow_data(workflow_id=workflow_id_1, name="Workflow 1")
        data_2 = create_workflow_data(workflow_id=workflow_id_2, name="Workflow 2")

        # Save versions for both workflows
        v1_1 = await version_store.save_version(workflow_id_1, data_1, "W1 V1")
        v2_1 = await version_store.save_version(workflow_id_2, data_2, "W2 V1")
        v1_2 = await version_store.save_version(workflow_id_1, data_1, "W1 V2")

        # Verify version numbers are independent
        version_1_1 = await version_store.get_version(v1_1)
        version_2_1 = await version_store.get_version(v2_1)
        version_1_2 = await version_store.get_version(v1_2)

        assert version_1_1["version_number"] == 1
        assert version_2_1["version_number"] == 1
        assert version_1_2["version_number"] == 2


class TestListVersions:
    """Test WorkflowVersionStore.list_versions method."""

    @pytest.mark.asyncio
    async def test_list_versions_empty(self, version_store, db_session):
        """Test listing versions when none exist."""
        workflow_id = create_workflow_id()

        versions = await version_store.list_versions(workflow_id)
        assert versions == []

    @pytest.mark.asyncio
    async def test_list_versions_returns_all(self, version_store, db_session):
        """Test listing returns all versions."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        # Create 3 versions
        await version_store.save_version(workflow_id, data, "V1")
        await version_store.save_version(workflow_id, data, "V2")
        await version_store.save_version(workflow_id, data, "V3")

        versions = await version_store.list_versions(workflow_id)
        assert len(versions) == 3

    @pytest.mark.asyncio
    async def test_list_versions_ordered_by_version_number(
        self, version_store, db_session
    ):
        """Test versions are ordered by version number descending."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        # Create versions
        await version_store.save_version(workflow_id, data, "V1")
        await version_store.save_version(workflow_id, data, "V2")
        await version_store.save_version(workflow_id, data, "V3")

        versions = await version_store.list_versions(workflow_id)

        # Should be in descending order (newest first)
        assert versions[0]["version_number"] == 3
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_list_versions_respects_limit(self, version_store, db_session):
        """Test list respects limit parameter."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        # Create 5 versions
        for i in range(5):
            await version_store.save_version(workflow_id, data, f"V{i+1}")

        versions = await version_store.list_versions(workflow_id, limit=3)
        assert len(versions) == 3

    @pytest.mark.asyncio
    async def test_list_versions_contains_metadata(self, version_store, db_session):
        """Test list returns correct metadata fields."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        await version_store.save_version(workflow_id, data, "Test message")

        versions = await version_store.list_versions(workflow_id)
        assert len(versions) == 1

        version = versions[0]
        assert "id" in version
        assert "workflow_id" in version
        assert "version_number" in version
        assert "message" in version
        assert "created_at" in version

        assert version["workflow_id"] == workflow_id
        assert version["version_number"] == 1
        assert version["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_list_versions_filters_by_workflow(
        self, version_store, db_session
    ):
        """Test list only returns versions for specified workflow."""
        workflow_id_1 = create_workflow_id()
        workflow_id_2 = create_workflow_id()

        data_1 = create_workflow_data(workflow_id=workflow_id_1)
        data_2 = create_workflow_data(workflow_id=workflow_id_2)

        # Create versions for both workflows
        await version_store.save_version(workflow_id_1, data_1, "W1 V1")
        await version_store.save_version(workflow_id_1, data_1, "W1 V2")
        await version_store.save_version(workflow_id_2, data_2, "W2 V1")

        # List for workflow 1
        versions_1 = await version_store.list_versions(workflow_id_1)
        assert len(versions_1) == 2
        assert all(v["workflow_id"] == workflow_id_1 for v in versions_1)

        # List for workflow 2
        versions_2 = await version_store.list_versions(workflow_id_2)
        assert len(versions_2) == 1
        assert versions_2[0]["workflow_id"] == workflow_id_2


class TestGetVersion:
    """Test WorkflowVersionStore.get_version method."""

    @pytest.mark.asyncio
    async def test_get_version_success(self, version_store, db_session):
        """Test getting version by ID."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        version_id = await version_store.save_version(
            workflow_id, data, "Test version"
        )

        version = await version_store.get_version(version_id)
        assert version is not None
        assert version["id"] == version_id
        assert version["workflow_id"] == workflow_id

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, version_store, db_session):
        """Test getting non-existent version returns None."""
        fake_id = str(uuid.uuid4())

        version = await version_store.get_version(fake_id)
        assert version is None

    @pytest.mark.asyncio
    async def test_get_version_includes_data(self, version_store, db_session):
        """Test get_version returns full workflow data."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id, name="Full Data Test")

        version_id = await version_store.save_version(workflow_id, data, "Data test")

        version = await version_store.get_version(version_id)
        assert "data" in version
        assert version["data"]["name"] == "Full Data Test"
        assert isinstance(version["data"]["nodes"], list)
        assert isinstance(version["data"]["edges"], list)

    @pytest.mark.asyncio
    async def test_get_version_all_fields(self, version_store, db_session):
        """Test get_version returns all required fields."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        version_id = await version_store.save_version(
            workflow_id, data, "All fields test"
        )

        version = await version_store.get_version(version_id)

        # Check all required fields
        assert "id" in version
        assert "workflow_id" in version
        assert "version_number" in version
        assert "message" in version
        assert "data" in version
        assert "created_at" in version

        assert version["message"] == "All fields test"
        assert version["version_number"] == 1


class TestRestoreVersion:
    """Test WorkflowVersionStore.restore_version method."""

    @pytest.mark.asyncio
    async def test_restore_version_success(self, version_store, db_session):
        """Test restoring workflow to version."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id, name="Original")

        version_id = await version_store.save_version(
            workflow_id, data, "Original version"
        )

        restored = await version_store.restore_version(version_id)

        assert restored is not None
        assert restored["name"] == "Original"
        assert restored["id"] == workflow_id

    @pytest.mark.asyncio
    async def test_restore_version_not_found(self, version_store, db_session):
        """Test restoring non-existent version raises error."""
        fake_id = str(uuid.uuid4())

        with pytest.raises(ValueError) as exc_info:
            await version_store.restore_version(fake_id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_restore_version_returns_full_data(
        self, version_store, db_session
    ):
        """Test restore returns complete workflow data."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id, name="Complete Data")

        version_id = await version_store.save_version(workflow_id, data, "Complete")

        restored = await version_store.restore_version(version_id)

        # Should have all workflow fields
        assert "id" in restored
        assert "name" in restored
        assert "description" in restored
        assert "nodes" in restored
        assert "edges" in restored
        assert "status" in restored

        assert restored["name"] == "Complete Data"
        assert len(restored["nodes"]) == 2
        assert len(restored["edges"]) == 1

    @pytest.mark.asyncio
    async def test_restore_older_version(self, version_store, db_session):
        """Test restoring to older version."""
        workflow_id = create_workflow_id()

        # Create version 1
        data_v1 = create_workflow_data(workflow_id=workflow_id, name="Version 1")
        version_id_1 = await version_store.save_version(
            workflow_id, data_v1, "V1"
        )

        # Create version 2
        data_v2 = create_workflow_data(workflow_id=workflow_id, name="Version 2")
        version_id_2 = await version_store.save_version(
            workflow_id, data_v2, "V2"
        )

        # Restore to version 1
        restored = await version_store.restore_version(version_id_1)

        assert restored["name"] == "Version 1"


class TestVersionStoreIntegration:
    """Integration tests for version store."""

    @pytest.mark.asyncio
    async def test_complete_version_lifecycle(self, version_store, db_session):
        """Test complete version lifecycle: save, list, get, restore."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id, name="Lifecycle Test")

        # 1. Save version
        version_id = await version_store.save_version(
            workflow_id, data, "Initial version"
        )
        assert version_id is not None

        # 2. List versions
        versions = await version_store.list_versions(workflow_id)
        assert len(versions) == 1
        assert versions[0]["id"] == version_id

        # 3. Get version
        version = await version_store.get_version(version_id)
        assert version["id"] == version_id
        assert version["data"]["name"] == "Lifecycle Test"

        # 4. Restore version
        restored = await version_store.restore_version(version_id)
        assert restored["name"] == "Lifecycle Test"

    @pytest.mark.asyncio
    async def test_version_numbers_increment_correctly(
        self, version_store, db_session
    ):
        """Test version numbers increment correctly across operations."""
        workflow_id = create_workflow_id()
        data = create_workflow_data(workflow_id=workflow_id)

        version_ids = []
        for i in range(5):
            version_id = await version_store.save_version(
                workflow_id, data, f"Version {i+1}"
            )
            version_ids.append(version_id)

        # Check all version numbers
        for i, version_id in enumerate(version_ids):
            version = await version_store.get_version(version_id)
            assert version["version_number"] == i + 1

    @pytest.mark.asyncio
    async def test_concurrent_workflow_versions(self, version_store, db_session):
        """Test managing versions for multiple workflows concurrently."""
        workflow_ids = [create_workflow_id() for _ in range(3)]

        # Create versions for each workflow
        for workflow_id in workflow_ids:
            data = create_workflow_data(workflow_id=workflow_id)
            for i in range(3):
                await version_store.save_version(
                    workflow_id, data, f"V{i+1}"
                )

        # Verify each workflow has correct versions
        for workflow_id in workflow_ids:
            versions = await version_store.list_versions(workflow_id)
            assert len(versions) == 3
            assert versions[0]["version_number"] == 3
            assert versions[1]["version_number"] == 2
            assert versions[2]["version_number"] == 1
