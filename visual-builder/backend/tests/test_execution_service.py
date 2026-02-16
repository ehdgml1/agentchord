"""Tests for execution service layer."""
import pytest
import json
from datetime import UTC, datetime
from app.models.execution import Execution
from app.models.workflow import Workflow as WorkflowModel
from app.core.executor import (
    ExecutionStatus,
    Workflow,
    WorkflowNode,
    WorkflowEdge,
)
from sqlalchemy import select
import uuid


class ExecutionService:
    """Service layer for execution operations."""

    def __init__(self, executor, db_session):
        self.executor = executor
        self.db_session = db_session

    async def start_execution(
        self,
        workflow_id: str,
        input_data: str,
        mode: str = "full",
        trigger_type: str = "manual",
    ) -> Execution:
        """Start new workflow execution."""
        # Get workflow from DB
        workflow_model = await self.db_session.get(WorkflowModel, workflow_id)
        if not workflow_model:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Convert to executor workflow
        workflow = self._model_to_workflow(workflow_model)

        # Create execution record
        execution_record = Execution(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            status="running",
            mode=mode,
            trigger_type=trigger_type,
            input=input_data,
            started_at=datetime.now(UTC).replace(tzinfo=None),
        )

        self.db_session.add(execution_record)
        await self.db_session.flush()

        # Execute workflow
        try:
            result = await self.executor.run(
                workflow=workflow,
                input=input_data,
                mode=mode,
                trigger_type=trigger_type,
            )

            # Update execution record
            execution_record.status = result.status.value
            execution_record.output = json.dumps(result.output) if result.output else None
            execution_record.error = result.error
            execution_record.completed_at = result.completed_at
            execution_record.node_logs = json.dumps([
                {
                    "node_id": ne.node_id,
                    "status": ne.status.value,
                    "output": str(ne.output),
                    "error": ne.error,
                    "duration_ms": ne.duration_ms,
                }
                for ne in result.node_executions
            ])

            await self.db_session.flush()

        except Exception as e:
            execution_record.status = "failed"
            execution_record.error = str(e)
            execution_record.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db_session.flush()
            raise

        return execution_record

    async def stop_execution(self, execution_id: str) -> bool:
        """Stop running execution."""
        execution = await self.db_session.get(Execution, execution_id)
        if not execution:
            return False

        if execution.status not in ["running", "pending"]:
            return False

        # Stop executor
        self.executor.stop(execution_id)

        # Update status
        execution.status = "cancelled"
        execution.completed_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db_session.flush()

        return True

    async def resume_execution(self, execution_id: str) -> Execution:
        """Resume paused execution."""
        execution = await self.db_session.get(Execution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status != "paused":
            raise ValueError(f"Execution {execution_id} is not paused")

        # Get workflow
        workflow_model = await self.db_session.get(WorkflowModel, execution.workflow_id)
        if not workflow_model:
            raise ValueError(f"Workflow {execution.workflow_id} not found")

        workflow = self._model_to_workflow(workflow_model)

        # Resume
        result = await self.executor.resume(execution_id, workflow)

        # Update record
        execution.status = result.status.value
        execution.output = json.dumps(result.output) if result.output else None
        execution.error = result.error
        execution.completed_at = result.completed_at
        await self.db_session.flush()

        return execution

    async def get_execution_logs(self, execution_id: str) -> list[dict]:
        """Retrieve node execution logs."""
        execution = await self.db_session.get(Execution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if not execution.node_logs:
            return []

        return json.loads(execution.node_logs)

    def _model_to_workflow(self, model: WorkflowModel) -> Workflow:
        """Convert DB model to executor workflow."""
        nodes_data = json.loads(model.nodes)
        edges_data = json.loads(model.edges)

        nodes = [
            WorkflowNode(
                id=n["id"],
                type=n["type"],
                data=n.get("data", {}),
                position=n.get("position"),
            )
            for n in nodes_data
        ]

        edges = [
            WorkflowEdge(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                source_handle=e.get("sourceHandle"),
                target_handle=e.get("targetHandle"),
            )
            for e in edges_data
        ]

        return Workflow(
            id=model.id,
            name=model.name,
            nodes=nodes,
            edges=edges,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


@pytest.fixture
async def execution_service(executor, db_session):
    """Create execution service."""
    return ExecutionService(executor, db_session)


@pytest.fixture
async def test_workflow_model(db_session):
    """Create test workflow in database."""
    workflow = WorkflowModel(
        id=str(uuid.uuid4()),
        name="Test Workflow",
        description="Test workflow for service tests",
        nodes=json.dumps([
            {
                "id": "node-1",
                "type": "agent",
                "data": {
                    "name": "Test Agent",
                    "model": "gpt-4o-mini",
                },
            },
        ]),
        edges=json.dumps([]),
        status="active",
    )

    db_session.add(workflow)
    await db_session.flush()
    return workflow


@pytest.mark.asyncio
async def test_start_execution(execution_service, test_workflow_model):
    """Test starting a new execution."""
    execution = await execution_service.start_execution(
        workflow_id=test_workflow_model.id,
        input_data="test input",
        mode="mock",
        trigger_type="manual",
    )

    assert execution.id is not None
    assert execution.workflow_id == test_workflow_model.id
    assert execution.status in ["completed", "running", "failed"]
    assert execution.input == "test input"
    assert execution.mode == "mock"
    assert execution.trigger_type == "manual"
    assert execution.started_at is not None


@pytest.mark.asyncio
async def test_start_execution_nonexistent_workflow(execution_service):
    """Test starting execution for non-existent workflow fails."""
    fake_workflow_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="not found"):
        await execution_service.start_execution(
            workflow_id=fake_workflow_id,
            input_data="test",
        )


@pytest.mark.asyncio
async def test_stop_execution(execution_service, test_workflow_model, db_session):
    """Test stopping a running execution."""
    # Create execution record
    execution = Execution(
        id=str(uuid.uuid4()),
        workflow_id=test_workflow_model.id,
        status="running",
        mode="full",
        trigger_type="manual",
        input="test",
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )

    db_session.add(execution)
    await db_session.flush()

    execution_id = execution.id

    # Stop execution
    result = await execution_service.stop_execution(execution_id)
    assert result is True

    # Verify status updated
    stopped_execution = await db_session.get(Execution, execution_id)
    assert stopped_execution.status == "cancelled"
    assert stopped_execution.completed_at is not None


@pytest.mark.asyncio
async def test_stop_nonexistent_execution(execution_service):
    """Test stopping non-existent execution returns False."""
    fake_id = str(uuid.uuid4())
    result = await execution_service.stop_execution(fake_id)
    assert result is False


@pytest.mark.asyncio
async def test_stop_completed_execution(execution_service, test_workflow_model, db_session):
    """Test stopping already completed execution returns False."""
    execution = Execution(
        id=str(uuid.uuid4()),
        workflow_id=test_workflow_model.id,
        status="completed",
        mode="full",
        trigger_type="manual",
        input="test",
        started_at=datetime.now(UTC).replace(tzinfo=None),
        completed_at=datetime.now(UTC).replace(tzinfo=None),
    )

    db_session.add(execution)
    await db_session.flush()

    result = await execution_service.stop_execution(execution.id)
    assert result is False


@pytest.mark.asyncio
async def test_resume_execution(execution_service, test_workflow_model, db_session, state_store):
    """Test resuming a paused execution."""
    execution_id = str(uuid.uuid4())

    # Create paused execution
    execution = Execution(
        id=execution_id,
        workflow_id=test_workflow_model.id,
        status="paused",
        mode="mock",
        trigger_type="manual",
        input="test input",
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )

    db_session.add(execution)
    await db_session.flush()

    # Save checkpoint
    await state_store.save_state(
        execution_id=execution_id,
        current_node="node-1",
        context={"input": "test input"},
    )

    # Resume
    resumed = await execution_service.resume_execution(execution_id)

    assert resumed.id == execution_id
    assert resumed.status in ["completed", "failed"]


@pytest.mark.asyncio
async def test_resume_nonexistent_execution(execution_service):
    """Test resuming non-existent execution raises error."""
    fake_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="not found"):
        await execution_service.resume_execution(fake_id)


@pytest.mark.asyncio
async def test_resume_non_paused_execution(execution_service, test_workflow_model, db_session):
    """Test resuming non-paused execution raises error."""
    execution = Execution(
        id=str(uuid.uuid4()),
        workflow_id=test_workflow_model.id,
        status="running",
        mode="full",
        trigger_type="manual",
        input="test",
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )

    db_session.add(execution)
    await db_session.flush()

    with pytest.raises(ValueError, match="not paused"):
        await execution_service.resume_execution(execution.id)


@pytest.mark.asyncio
async def test_get_execution_logs(execution_service, test_workflow_model, db_session):
    """Test retrieving execution logs."""
    node_logs = [
        {
            "node_id": "node-1",
            "status": "completed",
            "output": "test output",
            "error": None,
            "duration_ms": 100,
        },
        {
            "node_id": "node-2",
            "status": "completed",
            "output": "another output",
            "error": None,
            "duration_ms": 150,
        },
    ]

    execution = Execution(
        id=str(uuid.uuid4()),
        workflow_id=test_workflow_model.id,
        status="completed",
        mode="full",
        trigger_type="manual",
        input="test",
        node_logs=json.dumps(node_logs),
        started_at=datetime.now(UTC).replace(tzinfo=None),
        completed_at=datetime.now(UTC).replace(tzinfo=None),
    )

    db_session.add(execution)
    await db_session.flush()

    # Get logs
    logs = await execution_service.get_execution_logs(execution.id)

    assert len(logs) == 2
    assert logs[0]["node_id"] == "node-1"
    assert logs[0]["status"] == "completed"
    assert logs[1]["node_id"] == "node-2"


@pytest.mark.asyncio
async def test_get_logs_nonexistent_execution(execution_service):
    """Test getting logs for non-existent execution raises error."""
    fake_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="not found"):
        await execution_service.get_execution_logs(fake_id)


@pytest.mark.asyncio
async def test_get_logs_empty(execution_service, test_workflow_model, db_session):
    """Test getting logs when no logs exist."""
    execution = Execution(
        id=str(uuid.uuid4()),
        workflow_id=test_workflow_model.id,
        status="pending",
        mode="full",
        trigger_type="manual",
        input="test",
        node_logs="",
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )

    db_session.add(execution)
    await db_session.flush()

    logs = await execution_service.get_execution_logs(execution.id)
    assert logs == []
