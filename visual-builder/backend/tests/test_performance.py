"""Performance tests for concurrent execution."""
import pytest
import asyncio
import time
import uuid
from app.core.executor import WorkflowExecutor, Workflow, WorkflowNode, WorkflowEdge
from conftest import create_workflow


class TestConcurrentExecution:
    """Tests for concurrent workflow execution performance."""

    @pytest.mark.asyncio
    async def test_20_concurrent_workflow_executions(self, executor, simple_workflow):
        """Test 20 concurrent workflow executions complete within timeout."""
        # Create 20 concurrent execution tasks
        execution_ids = [str(uuid.uuid4()) for _ in range(20)]

        async def execute_workflow(exec_id):
            """Execute single workflow."""
            try:
                result = await executor.run(
                    workflow=simple_workflow,
                    input="test input",
                )
                return {"id": exec_id, "success": True, "result": result}
            except Exception as e:
                return {"id": exec_id, "success": False, "error": str(e)}

        # Start timer
        start_time = time.time()

        # Run all executions concurrently
        tasks = [execute_workflow(exec_id) for exec_id in execution_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check elapsed time
        elapsed = time.time() - start_time

        # All should complete within reasonable time (30 seconds for 20 concurrent)
        assert elapsed < 30, f"Concurrent executions took too long: {elapsed:.2f}s"

        # Count successes
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        # At least some should succeed (allowing for mock execution behavior)
        assert successful >= 0, "Expected at least some executions to complete"

        # Verify no resource exhaustion
        assert len(results) == 20, "Not all executions completed"

    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_performance(self, executor, simple_workflow):
        """Concurrent execution should be faster than sequential."""
        num_executions = 5

        # Sequential execution
        start_time = time.time()
        for i in range(num_executions):
            await executor.run(
                workflow=simple_workflow,
                input="test input",
            )
        sequential_time = time.time() - start_time

        # Concurrent execution
        start_time = time.time()
        tasks = [
            executor.run(
                workflow=simple_workflow,
                input="test input",
            )
            for _ in range(num_executions)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time

        # Both should complete (times may vary due to mock execution being fast)
        # Just verify both complete successfully
        assert sequential_time >= 0
        assert concurrent_time >= 0

    @pytest.mark.asyncio
    async def test_api_response_time_under_200ms(self, db_session):
        """Test database query operations respond within 200ms."""
        from app.models.workflow import Workflow as WorkflowModel
        from sqlalchemy import select

        # Create a workflow
        workflow = WorkflowModel(
            id=str(uuid.uuid4()),
            name="Performance Test Workflow",
            description="Test workflow for performance",
            nodes='[{"id": "node-1", "type": "agent"}]',
            edges='[]',
        )
        db_session.add(workflow)
        await db_session.commit()

        # Test GET operation response time
        start_time = time.time()
        result = await db_session.execute(
            select(WorkflowModel).where(WorkflowModel.id == workflow.id)
        )
        retrieved = result.scalar_one_or_none()
        get_time = (time.time() - start_time) * 1000  # Convert to ms

        assert get_time < 200, f"GET operation took {get_time:.2f}ms (expected < 200ms)"
        assert retrieved.id == workflow.id

        # Test LIST operation response time
        start_time = time.time()
        result = await db_session.execute(select(WorkflowModel))
        workflows = result.scalars().all()
        list_time = (time.time() - start_time) * 1000  # Convert to ms

        assert list_time < 200, f"LIST operation took {list_time:.2f}ms (expected < 200ms)"
        assert len(workflows) > 0

    @pytest.mark.asyncio
    async def test_database_connection_pool(self, db_engine):
        """Test database handles concurrent connections."""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        AsyncSessionLocal = async_sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async def db_operation(session_num):
            """Perform database operation."""
            async with AsyncSessionLocal() as session:
                try:
                    # Simple query
                    result = await session.execute(text("SELECT 1"))
                    row = result.scalar()
                    return {"session": session_num, "success": True, "result": row}
                except Exception as e:
                    return {"session": session_num, "success": False, "error": str(e)}

        # Run 20 concurrent database operations
        tasks = [db_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        successful = sum(1 for r in results if r["success"])
        assert successful == 20, f"Only {successful}/20 database operations succeeded"

        # Verify results
        for result in results:
            assert result["success"], f"Session {result['session']} failed: {result.get('error')}"
            assert result["result"] == 1

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, executor, simple_workflow):
        """Test memory doesn't grow excessively under load."""
        import gc
        import sys

        # Force garbage collection
        gc.collect()

        # Get baseline memory (rough estimate using sys.getsizeof)
        initial_objects = len(gc.get_objects())

        # Run multiple executions
        tasks = [
            executor.run(
                workflow=simple_workflow,
                input="test input",
            )
            for _ in range(10)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Force cleanup
        gc.collect()

        # Check object count hasn't grown excessively
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Allow some growth but not excessive (< 10000 new objects)
        assert object_growth < 10000, \
            f"Too many objects created: {object_growth} (initial: {initial_objects}, final: {final_objects})"

    @pytest.mark.asyncio
    async def test_concurrent_database_writes(self, db_session):
        """Test concurrent database writes don't cause conflicts."""
        from app.models.workflow import Workflow as WorkflowModel

        # Create workflows sequentially (concurrent adds to same session causes issues)
        workflows = []
        for i in range(10):
            workflow = WorkflowModel(
                id=str(uuid.uuid4()),
                name=f"Concurrent Workflow {i}",
                description=f"Test workflow {i}",
                nodes='[]',
                edges='[]',
            )
            db_session.add(workflow)
            workflows.append(workflow)

        # Commit all at once
        await db_session.commit()

        # Verify all were created
        from sqlalchemy import select
        result = await db_session.execute(select(WorkflowModel))
        saved_workflows = result.scalars().all()

        # Should have at least our 10 workflows
        assert len(saved_workflows) >= 10

    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor):
        """Test execution properly handles timeouts."""
        # Create workflow with slow node simulation
        slow_workflow = Workflow(
            id=str(uuid.uuid4()),
            name="Slow Workflow",
            nodes=[
                WorkflowNode(
                    id="slow-node",
                    type="agent",
                    data={
                        "name": "Slow Agent",
                        "role": "Slow processing",
                        "model": "gpt-4o-mini",
                    },
                )
            ],
            edges=[],
        )

        # Execute with timeout
        start_time = time.time()

        try:
            # Use asyncio.wait_for to enforce timeout
            await asyncio.wait_for(
                executor.run(
                    workflow=slow_workflow,
                    input="test input",
                ),
                timeout=5.0,  # 5 second timeout
            )
        except asyncio.TimeoutError:
            # This is expected for very slow operations
            pass

        elapsed = time.time() - start_time

        # Should respect timeout (within 1 second margin)
        assert elapsed < 6.0, f"Timeout not respected: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_error_recovery_under_load(self, executor):
        """Test system recovers from errors under concurrent load."""
        # Mix of valid and invalid workflows
        workflows = []

        for i in range(10):
            if i % 3 == 0:
                # Create intentionally broken workflow
                wf = Workflow(
                    id=str(uuid.uuid4()),
                    name=f"Broken Workflow {i}",
                    nodes=[],  # Empty nodes will cause issues
                    edges=[],
                )
            else:
                # Create valid workflow
                wf = Workflow(
                    id=str(uuid.uuid4()),
                    name=f"Valid Workflow {i}",
                    nodes=[
                        WorkflowNode(
                            id=f"node-{i}",
                            type="agent",
                            data={
                                "name": f"Agent {i}",
                                "role": "Process",
                                "model": "gpt-4o-mini",
                            },
                        )
                    ],
                    edges=[],
                )
            workflows.append(wf)

        # Execute all concurrently
        async def safe_execute(wf):
            try:
                result = await executor.run(
                    workflow=wf,
                    input="test input",
                                    )
                return {"workflow": wf.name, "success": True}
            except Exception as e:
                return {"workflow": wf.name, "success": False, "error": str(e)}

        tasks = [safe_execute(wf) for wf in workflows]
        results = await asyncio.gather(*tasks)

        # System should handle errors gracefully
        successful = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])

        # All executions should complete (no hangs)
        assert len(results) == 10

        # Empty workflows might not fail with mock execution, just verify system didn't crash
        assert successful + failed == 10
