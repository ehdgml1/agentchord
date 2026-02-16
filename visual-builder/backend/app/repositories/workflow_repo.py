"""Workflow repository implementation."""
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import Workflow
from app.repositories.interfaces import IWorkflowRepository


class WorkflowRepository(IWorkflowRepository):
    """Workflow repository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    async def create(
        self,
        workflow: Workflow,
    ) -> Workflow:
        """Create workflow.

        Args:
            workflow: Workflow entity

        Returns:
            Created workflow
        """
        self.session.add(workflow)
        await self.session.flush()
        return workflow

    async def get_by_id(
        self,
        workflow_id: str,
    ) -> Optional[Workflow]:
        """Get workflow by ID.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow or None
        """
        stmt = select(Workflow).where(
            Workflow.id == workflow_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> List[Workflow]:
        """List all workflows.

        Returns:
            List of workflows
        """
        stmt = select(Workflow).order_by(
            Workflow.created_at.desc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        workflow: Workflow,
    ) -> Workflow:
        """Update workflow.

        Args:
            workflow: Workflow entity

        Returns:
            Updated workflow
        """
        await self.session.merge(workflow)
        await self.session.flush()
        return workflow

    async def delete(
        self,
        workflow_id: str,
    ) -> bool:
        """Delete workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted
        """
        stmt = delete(Workflow).where(
            Workflow.id == workflow_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
