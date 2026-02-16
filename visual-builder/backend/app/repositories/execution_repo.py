"""Execution repository implementation."""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.execution import Execution
from app.repositories.interfaces import IExecutionRepository


class ExecutionRepository(IExecutionRepository):
    """Execution repository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    async def create(
        self,
        execution: Execution,
    ) -> Execution:
        """Create execution.

        Args:
            execution: Execution entity

        Returns:
            Created execution
        """
        self.session.add(execution)
        await self.session.flush()
        return execution

    async def get_by_id(
        self,
        execution_id: str,
    ) -> Optional[Execution]:
        """Get execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            Execution or None
        """
        stmt = select(Execution).where(
            Execution.id == execution_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workflow(
        self,
        workflow_id: str,
    ) -> List[Execution]:
        """List executions by workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of executions
        """
        stmt = select(Execution).where(
            Execution.workflow_id == workflow_id
        ).order_by(
            Execution.started_at.desc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        execution: Execution,
    ) -> Execution:
        """Update execution.

        Args:
            execution: Execution entity

        Returns:
            Updated execution
        """
        await self.session.merge(execution)
        await self.session.flush()
        return execution
