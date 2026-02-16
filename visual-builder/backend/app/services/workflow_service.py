"""Workflow service layer.

Phase -1 아키텍처 스파이크:
- API와 Core 사이의 서비스 레이어
- 감사 로깅 통합
- 워크플로우 검증
- 트랜잭션 경계 관리
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Protocol

from ..core.executor import (
    WorkflowExecutor,
    WorkflowExecution,
    Workflow,
    WorkflowValidationError,
)
from .audit_service import AuditService


class User(Protocol):
    """User interface."""
    id: str
    email: str
    role: str


class IWorkflowRepository(Protocol):
    """Workflow repository interface."""

    async def get_by_id(self, workflow_id: str) -> Workflow | None:
        """Get workflow by ID."""
        ...

    async def save(self, workflow: Workflow) -> None:
        """Save workflow."""
        ...

    async def delete(self, workflow_id: str) -> None:
        """Delete workflow."""
        ...

    async def list(
        self,
        owner_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Workflow]:
        """List workflows."""
        ...


class WorkflowNotFoundError(Exception):
    """Workflow not found."""
    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow '{workflow_id}' not found")
        self.workflow_id = workflow_id


class WorkflowService:
    """Service layer for workflow operations.

    Provides:
        - Business logic between API and Core
        - Audit logging
        - Workflow validation
        - Error handling

    Example:
        >>> service = WorkflowService(executor, repository, audit_service)
        >>> execution = await service.run_workflow(
        ...     workflow_id="wf-123",
        ...     input="Hello",
        ...     mode="full",
        ...     user=current_user,
        ... )
    """

    def __init__(
        self,
        executor: WorkflowExecutor,
        repository: IWorkflowRepository,
        audit_service: AuditService,
    ) -> None:
        """Initialize service.

        Args:
            executor: Workflow executor.
            repository: Workflow repository.
            audit_service: Audit logging service.
        """
        self.executor = executor
        self.repository = repository
        self.audit_service = audit_service

    async def run_workflow(
        self,
        workflow_id: str,
        input: str,
        mode: str,
        user: User,
        trigger_type: str = "manual",
        trigger_id: str | None = None,
        ip_address: str | None = None,
    ) -> WorkflowExecution:
        """Execute workflow with audit logging.

        Args:
            workflow_id: Workflow ID to execute.
            input: Workflow input string.
            mode: Execution mode ("full", "mock", "debug").
            user: User executing the workflow.
            trigger_type: How execution was triggered.
            trigger_id: ID of schedule/webhook if applicable.
            ip_address: Client IP address.

        Returns:
            Workflow execution result.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
            WorkflowValidationError: If workflow is invalid.
        """
        # Get workflow
        workflow = await self.repository.get_by_id(workflow_id)
        if not workflow:
            # Log failed attempt
            await self.audit_service.log(
                action="execute",
                resource_type="workflow",
                resource_id=workflow_id,
                user_id=user.id,
                details={"mode": mode, "error": "not_found"},
                ip_address=ip_address,
                success=False,
            )
            raise WorkflowNotFoundError(workflow_id)

        # Log execution start
        await self.audit_service.log(
            action="execute",
            resource_type="workflow",
            resource_id=workflow_id,
            user_id=user.id,
            details={
                "mode": mode,
                "trigger_type": trigger_type,
                "trigger_id": trigger_id,
            },
            ip_address=ip_address,
            success=True,
        )

        # Execute workflow
        try:
            execution = await self.executor.run(
                workflow=workflow,
                input=input,
                mode=mode,
                trigger_type=trigger_type,
                trigger_id=trigger_id,
            )
            return execution

        except WorkflowValidationError:
            # Log validation failure
            await self.audit_service.log(
                action="execute",
                resource_type="workflow",
                resource_id=workflow_id,
                user_id=user.id,
                details={"mode": mode, "error": "validation_failed"},
                ip_address=ip_address,
                success=False,
            )
            raise

    async def get_workflow(
        self,
        workflow_id: str,
        user: User,
    ) -> Workflow:
        """Get workflow by ID.

        Args:
            workflow_id: Workflow ID.
            user: User requesting the workflow.

        Returns:
            Workflow instance.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        workflow = await self.repository.get_by_id(workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    async def create_workflow(
        self,
        workflow: Workflow,
        user: User,
        ip_address: str | None = None,
    ) -> Workflow:
        """Create new workflow.

        Args:
            workflow: Workflow to create.
            user: User creating the workflow.
            ip_address: Client IP address.

        Returns:
            Created workflow.
        """
        await self.repository.save(workflow)

        await self.audit_service.log(
            action="create",
            resource_type="workflow",
            resource_id=workflow.id,
            user_id=user.id,
            details={"name": workflow.name},
            ip_address=ip_address,
            success=True,
        )

        return workflow

    async def update_workflow(
        self,
        workflow: Workflow,
        user: User,
        ip_address: str | None = None,
    ) -> Workflow:
        """Update existing workflow.

        Args:
            workflow: Workflow with updates.
            user: User updating the workflow.
            ip_address: Client IP address.

        Returns:
            Updated workflow.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        existing = await self.repository.get_by_id(workflow.id)
        if not existing:
            raise WorkflowNotFoundError(workflow.id)

        workflow.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.repository.save(workflow)

        await self.audit_service.log(
            action="update",
            resource_type="workflow",
            resource_id=workflow.id,
            user_id=user.id,
            details={"name": workflow.name},
            ip_address=ip_address,
            success=True,
        )

        return workflow

    async def delete_workflow(
        self,
        workflow_id: str,
        user: User,
        ip_address: str | None = None,
    ) -> None:
        """Delete workflow.

        Args:
            workflow_id: Workflow ID to delete.
            user: User deleting the workflow.
            ip_address: Client IP address.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        existing = await self.repository.get_by_id(workflow_id)
        if not existing:
            raise WorkflowNotFoundError(workflow_id)

        await self.repository.delete(workflow_id)

        await self.audit_service.log(
            action="delete",
            resource_type="workflow",
            resource_id=workflow_id,
            user_id=user.id,
            ip_address=ip_address,
            success=True,
        )

    async def validate_workflow(
        self,
        workflow: Workflow,
    ) -> list[str]:
        """Validate workflow without executing.

        Args:
            workflow: Workflow to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        # Node count
        if len(workflow.nodes) > 100:
            errors.append(
                f"Workflow has {len(workflow.nodes)} nodes, maximum is 100"
            )

        # Cycle detection
        if self.executor._has_cycle(workflow):
            errors.append("Workflow contains a cycle")

        # Orphan nodes
        orphans = self.executor._find_orphan_nodes(workflow)
        if orphans:
            errors.append(f"Workflow has orphan nodes: {orphans}")

        # Check for required fields in nodes
        for node in workflow.nodes:
            if node.type == "agent":
                if not node.data.get("model"):
                    errors.append(f"Agent node '{node.id}' missing model")
            elif node.type == "mcp_tool":
                if not node.data.get("serverId"):
                    errors.append(f"MCP tool node '{node.id}' missing serverId")
                if not node.data.get("toolName"):
                    errors.append(f"MCP tool node '{node.id}' missing toolName")

        return errors
