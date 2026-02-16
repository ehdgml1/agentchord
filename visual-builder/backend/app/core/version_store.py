"""Workflow version management."""
import json
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.version import WorkflowVersion
from app.repositories.version_repo import VersionRepository


class WorkflowVersionStore:
    """Manages workflow versions."""

    def __init__(self, session: AsyncSession):
        """Initialize version store.

        Args:
            session: Database session
        """
        self.session = session
        self.repo = VersionRepository(session)

    async def save_version(
        self,
        workflow_id: str,
        data: dict,
        message: str = "",
    ) -> str:
        """Save workflow version.

        Args:
            workflow_id: Workflow ID
            data: Workflow data to version
            message: Optional version message

        Returns:
            Version ID
        """
        version_number = await self.repo.get_next_version_number(
            workflow_id
        )

        version = WorkflowVersion(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            version_number=version_number,
            data=json.dumps(data),
            message=message or f"Version {version_number}",
        )

        created = await self.repo.create(version)
        return created.id

    async def list_versions(
        self,
        workflow_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """List workflow versions.

        Args:
            workflow_id: Workflow ID
            limit: Max versions

        Returns:
            List of version metadata
        """
        versions = await self.repo.list_by_workflow(
            workflow_id,
            limit,
        )

        return [
            {
                "id": v.id,
                "workflow_id": v.workflow_id,
                "version_number": v.version_number,
                "message": v.message,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ]

    async def get_version(
        self,
        version_id: str,
    ) -> Optional[dict]:
        """Get specific version.

        Args:
            version_id: Version ID

        Returns:
            Version data or None
        """
        version = await self.repo.get_by_id(version_id)
        if not version:
            return None

        return {
            "id": version.id,
            "workflow_id": version.workflow_id,
            "version_number": version.version_number,
            "message": version.message,
            "data": json.loads(version.data),
            "created_at": version.created_at.isoformat(),
        }

    async def restore_version(
        self,
        version_id: str,
    ) -> dict:
        """Restore workflow to version.

        Args:
            version_id: Version ID

        Returns:
            Restored workflow data

        Raises:
            ValueError: Version not found
        """
        version_data = await self.get_version(version_id)
        if not version_data:
            raise ValueError(f"Version {version_id} not found")

        return version_data["data"]
