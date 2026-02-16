"""Repository interfaces."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, List, Optional
from app.models.workflow import Workflow
from app.models.execution import Execution
from app.models.schedule import Schedule


class IWorkflowRepository(ABC):
    """Workflow repository interface."""

    @abstractmethod
    async def create(
        self,
        workflow: Workflow,
    ) -> Workflow:
        """Create workflow."""
        pass

    @abstractmethod
    async def get_by_id(
        self,
        workflow_id: str,
    ) -> Optional[Workflow]:
        """Get workflow by ID."""
        pass

    @abstractmethod
    async def list_all(self) -> List[Workflow]:
        """List all workflows."""
        pass

    @abstractmethod
    async def update(
        self,
        workflow: Workflow,
    ) -> Workflow:
        """Update workflow."""
        pass

    @abstractmethod
    async def delete(
        self,
        workflow_id: str,
    ) -> bool:
        """Delete workflow."""
        pass


class IExecutionRepository(ABC):
    """Execution repository interface."""

    @abstractmethod
    async def create(
        self,
        execution: Execution,
    ) -> Execution:
        """Create execution."""
        pass

    @abstractmethod
    async def get_by_id(
        self,
        execution_id: str,
    ) -> Optional[Execution]:
        """Get execution by ID."""
        pass

    @abstractmethod
    async def list_by_workflow(
        self,
        workflow_id: str,
    ) -> List[Execution]:
        """List executions by workflow."""
        pass

    @abstractmethod
    async def update(
        self,
        execution: Execution,
    ) -> Execution:
        """Update execution."""
        pass


class IScheduleRepository(ABC):
    """Schedule repository interface."""

    @abstractmethod
    async def create(
        self,
        workflow_id: str,
        expression: str,
        input_data: dict[str, Any] | None = None,
        timezone: str = "UTC",
    ) -> Schedule:
        """Create schedule."""
        pass

    @abstractmethod
    async def get_by_id(
        self,
        schedule_id: str,
    ) -> Optional[Schedule]:
        """Get schedule by ID."""
        pass

    @abstractmethod
    async def list_by_workflow(
        self,
        workflow_id: str,
    ) -> List[Schedule]:
        """List schedules by workflow."""
        pass

    @abstractmethod
    async def list_all_enabled(self) -> List[Schedule]:
        """List all enabled schedules."""
        pass

    @abstractmethod
    async def update(
        self,
        schedule_id: str,
        expression: str | None = None,
        input_data: dict[str, Any] | None = None,
        timezone: str | None = None,
        enabled: bool | None = None,
    ) -> Optional[Schedule]:
        """Update schedule."""
        pass

    @abstractmethod
    async def delete(
        self,
        schedule_id: str,
    ) -> bool:
        """Delete schedule."""
        pass

    @abstractmethod
    async def update_last_run(
        self,
        schedule_id: str,
        timestamp: datetime,
    ) -> None:
        """Update last run timestamp."""
        pass

    @abstractmethod
    async def update_next_run(
        self,
        schedule_id: str,
        timestamp: datetime | None,
    ) -> None:
        """Update next run timestamp."""
        pass
