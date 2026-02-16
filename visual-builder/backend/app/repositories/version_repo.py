"""WorkflowVersion repository implementation."""
from typing import List, Optional
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.version import WorkflowVersion


class VersionRepository:
    """Version repository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    async def create(
        self,
        version: WorkflowVersion,
    ) -> WorkflowVersion:
        """Create version.

        Args:
            version: Version entity

        Returns:
            Created version
        """
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_by_id(
        self,
        version_id: str,
    ) -> Optional[WorkflowVersion]:
        """Get version by ID.

        Args:
            version_id: Version ID

        Returns:
            Version or None
        """
        stmt = select(WorkflowVersion).where(
            WorkflowVersion.id == version_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workflow(
        self,
        workflow_id: str,
        limit: int = 50,
    ) -> List[WorkflowVersion]:
        """List versions for workflow.

        Args:
            workflow_id: Workflow ID
            limit: Max versions to return

        Returns:
            List of versions
        """
        stmt = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(WorkflowVersion.version_number.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_next_version_number(
        self,
        workflow_id: str,
    ) -> int:
        """Get next version number.

        Args:
            workflow_id: Workflow ID

        Returns:
            Next version number
        """
        stmt = select(
            func.max(WorkflowVersion.version_number)
        ).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        result = await self.session.execute(stmt)
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def delete_by_workflow(
        self,
        workflow_id: str,
    ) -> int:
        """Delete all versions for workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Number of deleted versions
        """
        stmt = delete(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount
