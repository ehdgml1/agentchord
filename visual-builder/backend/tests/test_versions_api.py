"""Tests for versions API endpoints.

Tests GET, POST operations for /api/workflows/{workflow_id}/versions endpoints
using TestClient and factory functions (no hardcoded data).
"""
import pytest
import pytest_asyncio
import json
import uuid
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.versions import router
from app.db.database import get_db
from app.auth import get_current_user
from app.auth.jwt import User
from app.core.rbac import Role
from app.models.workflow import Workflow as WorkflowModel
from app.repositories.workflow_repo import WorkflowRepository
from app.core.version_store import WorkflowVersionStore


# Factory functions for test data
def create_workflow_factory(
    workflow_id: str | None = None,
    name: str = "Test Workflow",
    nodes: list | None = None,
    edges: list | None = None,
) -> WorkflowModel:
    """Factory function to create workflow model."""
    if nodes is None:
        nodes = [
            {
                "id": "node-1",
                "type": "agent",
                "data": {"name": "Test Agent", "model": "gpt-4o-mini"},
            }
        ]

    if edges is None:
        edges = []

    return WorkflowModel(
        id=workflow_id or str(uuid.uuid4()),
        name=name,
        description="Test workflow description",
        nodes=json.dumps(nodes),
        edges=json.dumps(edges),
        status="active",
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )


def create_version_payload(message: str = "Test version") -> dict:
    """Factory function to create version creation payload."""
    return {"message": message}


def create_mock_user() -> User:
    """Factory function to create mock user."""
    return User(
        id=str(uuid.uuid4()),
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
async def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def sample_workflow(db_session):
    """Create sample workflow in database."""
    workflow_repo = WorkflowRepository(db_session)
    workflow = create_workflow_factory()
    created = await workflow_repo.create(workflow)
    await db_session.commit()
    return created


class TestListVersions:
    """Test GET /api/workflows/{workflow_id}/versions endpoint."""

    @pytest.mark.asyncio
    async def test_list_versions_empty(self, client, sample_workflow):
        """Test listing versions when none exist."""
        response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions"
        )

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert "total" in data
        assert data["versions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_versions_not_found(self, client):
        """Test listing versions for non-existent workflow."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/workflows/{fake_id}/versions")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "WORKFLOW_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_versions_with_data(
        self, client, sample_workflow, db_session
    ):
        """Test listing versions returns all versions."""
        version_store = WorkflowVersionStore(db_session)

        # Create versions
        workflow_data = {
            "id": sample_workflow.id,
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        await version_store.save_version(
            sample_workflow.id, workflow_data, "Version 1"
        )
        await version_store.save_version(
            sample_workflow.id, workflow_data, "Version 2"
        )
        await version_store.save_version(
            sample_workflow.id, workflow_data, "Version 3"
        )
        await db_session.commit()

        # List versions
        response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["versions"]) == 3

        # Verify versions are in descending order
        assert data["versions"][0]["versionNumber"] == 3
        assert data["versions"][1]["versionNumber"] == 2
        assert data["versions"][2]["versionNumber"] == 1

    @pytest.mark.asyncio
    async def test_list_versions_metadata_fields(
        self, client, sample_workflow, db_session
    ):
        """Test list returns correct metadata fields."""
        version_store = WorkflowVersionStore(db_session)

        workflow_data = {
            "id": sample_workflow.id,
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        await version_store.save_version(
            sample_workflow.id, workflow_data, "Test message"
        )
        await db_session.commit()

        response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions"
        )

        assert response.status_code == 200
        data = response.json()
        version = data["versions"][0]

        assert "id" in version
        assert "workflowId" in version
        assert "versionNumber" in version
        assert "message" in version
        assert "createdAt" in version
        assert version["message"] == "Test message"


class TestGetVersion:
    """Test GET /api/workflows/{workflow_id}/versions/{version_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_version_success(
        self, client, sample_workflow, db_session
    ):
        """Test getting specific version."""
        version_store = WorkflowVersionStore(db_session)

        workflow_data = {
            "id": sample_workflow.id,
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        version_id = await version_store.save_version(
            sample_workflow.id, workflow_data, "Get test"
        )
        await db_session.commit()

        response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions/{version_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == version_id
        assert data["workflowId"] == sample_workflow.id
        assert data["message"] == "Get test"
        assert "data" in data
        assert data["data"]["name"] == sample_workflow.name

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, client, sample_workflow):
        """Test getting non-existent version."""
        fake_version_id = str(uuid.uuid4())
        response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions/{fake_version_id}"
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "VERSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_version_wrong_workflow(
        self, client, sample_workflow, db_session
    ):
        """Test getting version with mismatched workflow ID."""
        version_store = WorkflowVersionStore(db_session)

        workflow_data = {
            "id": sample_workflow.id,
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        version_id = await version_store.save_version(
            sample_workflow.id, workflow_data, "Test"
        )
        await db_session.commit()

        # Try with different workflow ID
        wrong_workflow_id = str(uuid.uuid4())
        response = client.get(
            f"/api/workflows/{wrong_workflow_id}/versions/{version_id}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_version_includes_full_data(
        self, client, sample_workflow, db_session
    ):
        """Test get version returns complete workflow data."""
        version_store = WorkflowVersionStore(db_session)

        workflow_data = {
            "id": sample_workflow.id,
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        version_id = await version_store.save_version(
            sample_workflow.id, workflow_data, "Full data"
        )
        await db_session.commit()

        response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions/{version_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "nodes" in data["data"]
        assert "edges" in data["data"]
        assert isinstance(data["data"]["nodes"], list)
        assert isinstance(data["data"]["edges"], list)


class TestCreateVersion:
    """Test POST /api/workflows/{workflow_id}/versions endpoint."""

    @pytest.mark.asyncio
    async def test_create_version_success(self, client, sample_workflow):
        """Test creating workflow version."""
        payload = create_version_payload("First version")

        response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=payload,
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["workflowId"] == sample_workflow.id
        assert data["versionNumber"] == 1
        assert data["message"] == "First version"
        assert "createdAt" in data

    @pytest.mark.asyncio
    async def test_create_version_workflow_not_found(self, client):
        """Test creating version for non-existent workflow."""
        fake_id = str(uuid.uuid4())
        payload = create_version_payload()

        response = client.post(
            f"/api/workflows/{fake_id}/versions",
            json=payload,
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "WORKFLOW_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_version_increments_number(
        self, client, sample_workflow
    ):
        """Test version numbers increment correctly."""
        # Create first version
        response1 = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=create_version_payload("V1"),
        )
        assert response1.status_code == 201
        assert response1.json()["versionNumber"] == 1

        # Create second version
        response2 = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=create_version_payload("V2"),
        )
        assert response2.status_code == 201
        assert response2.json()["versionNumber"] == 2

        # Create third version
        response3 = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=create_version_payload("V3"),
        )
        assert response3.status_code == 201
        assert response3.json()["versionNumber"] == 3

    @pytest.mark.asyncio
    async def test_create_version_persists_workflow_data(
        self, client, sample_workflow, db_session
    ):
        """Test version captures current workflow state."""
        # Create version
        response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=create_version_payload("Snapshot"),
        )
        assert response.status_code == 201
        version_id = response.json()["id"]

        # Verify data was captured
        version_store = WorkflowVersionStore(db_session)
        version = await version_store.get_version(version_id)

        assert version["data"]["name"] == sample_workflow.name
        assert version["data"]["description"] == sample_workflow.description
        assert len(version["data"]["nodes"]) == len(
            json.loads(sample_workflow.nodes)
        )

    @pytest.mark.asyncio
    async def test_create_version_with_custom_message(
        self, client, sample_workflow
    ):
        """Test creating version with custom message."""
        custom_message = "Added new node for data processing"
        payload = create_version_payload(custom_message)

        response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=payload,
        )

        assert response.status_code == 201
        assert response.json()["message"] == custom_message


class TestRestoreVersion:
    """Test POST /api/workflows/{workflow_id}/versions/{version_id}/restore endpoint."""

    @pytest.mark.asyncio
    async def test_restore_version_success(
        self, client, sample_workflow, db_session
    ):
        """Test restoring workflow to version."""
        version_store = WorkflowVersionStore(db_session)
        workflow_repo = WorkflowRepository(db_session)

        # Save original state
        original_data = {
            "id": sample_workflow.id,
            "name": "Original Name",
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        version_id = await version_store.save_version(
            sample_workflow.id, original_data, "Original"
        )
        await db_session.commit()

        # Modify workflow
        sample_workflow.name = "Modified Name"
        await workflow_repo.update(sample_workflow)
        await db_session.commit()

        # Restore version
        response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions/{version_id}/restore"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflowId"] == sample_workflow.id
        assert data["versionId"] == version_id
        assert data["versionNumber"] == 1
        assert "Successfully restored" in data["message"]

        # Verify workflow was restored
        await db_session.refresh(sample_workflow)
        assert sample_workflow.name == "Original Name"

    @pytest.mark.asyncio
    async def test_restore_version_not_found(self, client, sample_workflow):
        """Test restoring non-existent version."""
        fake_version_id = str(uuid.uuid4())
        response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions/{fake_version_id}/restore"
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "VERSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_restore_version_wrong_workflow(
        self, client, sample_workflow, db_session
    ):
        """Test restoring version to wrong workflow."""
        version_store = WorkflowVersionStore(db_session)

        # Create version for sample_workflow
        workflow_data = {
            "id": sample_workflow.id,
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "nodes": json.loads(sample_workflow.nodes),
            "edges": json.loads(sample_workflow.edges),
            "status": sample_workflow.status,
        }

        version_id = await version_store.save_version(
            sample_workflow.id, workflow_data, "Test"
        )
        await db_session.commit()

        # Try to restore to different workflow
        wrong_workflow_id = str(uuid.uuid4())
        response = client.post(
            f"/api/workflows/{wrong_workflow_id}/versions/{version_id}/restore"
        )

        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_restore_version_updates_all_fields(
        self, client, sample_workflow, db_session
    ):
        """Test restore updates all workflow fields."""
        version_store = WorkflowVersionStore(db_session)
        workflow_repo = WorkflowRepository(db_session)

        # Save original state with specific data
        original_nodes = [
            {"id": "original-1", "type": "agent", "data": {"name": "Original"}},
            {"id": "original-2", "type": "agent", "data": {"name": "Original 2"}},
        ]
        original_edges = [{"id": "edge-1", "source": "original-1", "target": "original-2"}]

        original_data = {
            "id": sample_workflow.id,
            "name": "Original Workflow",
            "description": "Original description",
            "nodes": original_nodes,
            "edges": original_edges,
            "status": "active",
        }

        version_id = await version_store.save_version(
            sample_workflow.id, original_data, "Original state"
        )
        await db_session.commit()

        # Modify workflow completely
        sample_workflow.name = "Modified"
        sample_workflow.description = "Modified description"
        sample_workflow.nodes = json.dumps([{"id": "new-1", "type": "agent", "data": {}}])
        sample_workflow.edges = json.dumps([])
        await workflow_repo.update(sample_workflow)
        await db_session.commit()

        # Restore
        response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions/{version_id}/restore"
        )
        assert response.status_code == 200

        # Verify all fields restored
        await db_session.refresh(sample_workflow)
        assert sample_workflow.name == "Original Workflow"
        assert sample_workflow.description == "Original description"

        restored_nodes = json.loads(sample_workflow.nodes)
        assert len(restored_nodes) == 2
        assert restored_nodes[0]["id"] == "original-1"

        restored_edges = json.loads(sample_workflow.edges)
        assert len(restored_edges) == 1


class TestVersionsAPIIntegration:
    """Integration tests for versions API."""

    @pytest.mark.asyncio
    async def test_complete_version_workflow(
        self, client, sample_workflow, db_session
    ):
        """Test complete version workflow: create, list, get, restore."""
        # 1. Create version
        create_response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions",
            json=create_version_payload("Initial version"),
        )
        assert create_response.status_code == 201
        version_id = create_response.json()["id"]

        # 2. List versions
        list_response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        # 3. Get version
        get_response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions/{version_id}"
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == version_id

        # 4. Restore version
        restore_response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions/{version_id}/restore"
        )
        assert restore_response.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_versions_workflow(self, client, sample_workflow):
        """Test creating and managing multiple versions."""
        # Create multiple versions
        version_ids = []
        for i in range(3):
            response = client.post(
                f"/api/workflows/{sample_workflow.id}/versions",
                json=create_version_payload(f"Version {i+1}"),
            )
            assert response.status_code == 201
            version_ids.append(response.json()["id"])

        # List should show all versions
        list_response = client.get(
            f"/api/workflows/{sample_workflow.id}/versions"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 3

        # Can get each version
        for version_id in version_ids:
            response = client.get(
                f"/api/workflows/{sample_workflow.id}/versions/{version_id}"
            )
            assert response.status_code == 200

        # Can restore any version
        restore_response = client.post(
            f"/api/workflows/{sample_workflow.id}/versions/{version_ids[0]}/restore"
        )
        assert restore_response.status_code == 200
