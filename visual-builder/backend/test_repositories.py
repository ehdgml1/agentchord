"""Test repository implementations."""
import asyncio
import uuid
from datetime import datetime
from app.db import init_db, AsyncSessionLocal
from app.models.workflow import Workflow
from app.models.execution import Execution
from app.repositories import WorkflowRepository, ExecutionRepository


async def test_workflow_repo():
    """Test workflow repository."""
    print("\n=== Testing Workflow Repository ===")

    async with AsyncSessionLocal() as session:
        repo = WorkflowRepository(session)

        # Create workflow
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            id=workflow_id,
            name="Test Workflow",
            description="Test description",
            nodes="[]",
            edges="[]",
            status="draft",
        )

        created = await repo.create(workflow)
        await session.commit()
        print(f"✓ Created workflow: {created.id}")

        # Get by ID
        found = await repo.get_by_id(workflow_id)
        assert found is not None
        assert found.name == "Test Workflow"
        print(f"✓ Found workflow: {found.name}")

        # Update workflow
        found.status = "published"
        updated = await repo.update(found)
        await session.commit()
        print(f"✓ Updated workflow status: {updated.status}")

        # List all
        workflows = await repo.list_all()
        assert len(workflows) >= 1
        print(f"✓ Listed {len(workflows)} workflow(s)")

        # Delete workflow
        deleted = await repo.delete(workflow_id)
        await session.commit()
        assert deleted is True
        print(f"✓ Deleted workflow")


async def test_execution_repo():
    """Test execution repository."""
    print("\n=== Testing Execution Repository ===")

    async with AsyncSessionLocal() as session:
        # Create workflow first
        workflow_repo = WorkflowRepository(session)
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            id=workflow_id,
            name="Test Workflow for Execution",
            description="Test",
            nodes="[]",
            edges="[]",
            status="published",
        )
        await workflow_repo.create(workflow)
        await session.commit()
        print(f"✓ Created workflow: {workflow.id}")

        # Create execution
        exec_repo = ExecutionRepository(session)
        exec_id = str(uuid.uuid4())
        execution = Execution(
            id=exec_id,
            workflow_id=workflow_id,
            status="pending",
            mode="full",
            trigger_type="manual",
            input="{}",
            node_logs="[]",
        )

        created = await exec_repo.create(execution)
        await session.commit()
        print(f"✓ Created execution: {created.id}")

        # Get by ID
        found = await exec_repo.get_by_id(exec_id)
        assert found is not None
        assert found.status == "pending"
        print(f"✓ Found execution: {found.status}")

        # Update execution
        found.status = "completed"
        found.output = '{"result": "success"}'
        updated = await exec_repo.update(found)
        await session.commit()
        print(f"✓ Updated execution status: {updated.status}")

        # List by workflow
        executions = await exec_repo.list_by_workflow(workflow_id)
        assert len(executions) >= 1
        print(f"✓ Listed {len(executions)} execution(s)")

        # Cleanup
        await workflow_repo.delete(workflow_id)
        await session.commit()
        print(f"✓ Cleaned up test data")


async def main():
    """Run all tests."""
    print("Initializing database...")
    await init_db()
    print("✓ Database initialized")

    await test_workflow_repo()
    await test_execution_repo()

    print("\n=== All Tests Passed! ===\n")


if __name__ == "__main__":
    asyncio.run(main())
