"""Shared test fixtures for Phase 1 features."""
import os

# Set test environment variables BEFORE any app imports
# This ensures JWT_SECRET is set when jwt.py module is loaded
if not os.environ.get("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"
if not os.environ.get("SECRET_KEY"):
    from cryptography.fernet import Fernet
    os.environ["SECRET_KEY"] = Fernet.generate_key().decode()

import asyncio
import pytest
import pytest_asyncio
from datetime import UTC, datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import sys
import uuid
from pathlib import Path

# Add agentweave to path
_agentweave_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _agentweave_root not in sys.path:
    sys.path.insert(0, _agentweave_root)

# Import app modules
from app.db.database import Base
from app.models.workflow import Workflow as WorkflowModel
from app.models.execution import Execution as ExecutionModel
from app.models.schedule import Schedule as ScheduleModel
from app.core.executor import (
    WorkflowExecutor,
    ExecutionStateStore,
    Workflow,
    WorkflowNode,
    WorkflowEdge,
)
from app.core.mcp_manager import MCPManager
from app.core.secret_store import SecretStore


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    from sqlalchemy import text

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create execution_states table (used by executor)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS execution_states (
                execution_id TEXT PRIMARY KEY,
                current_node TEXT NOT NULL,
                context TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    AsyncSessionLocal = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def mock_mcp_manager():
    """Create mock MCP manager."""
    class MockMCPManager:
        def __init__(self):
            # Initialize empty tools dictionary for MCP tool binding
            self._tools = {}

        async def execute_tool(self, server_id: str, tool_name: str, arguments: dict):
            """Mock tool execution."""
            return {
                "result": f"Mock result for {tool_name}",
                "server_id": server_id,
                "arguments": arguments,
            }

        async def connect_server(self, server_id: str):
            """Mock connect."""
            pass

        async def disconnect_server(self, server_id: str):
            """Mock disconnect."""
            pass

    return MockMCPManager()


@pytest_asyncio.fixture
async def secret_store(db_engine):
    """Create secret store."""
    # Create secrets table if needed
    from sqlalchemy import text

    async with db_engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS secrets (
                name TEXT NOT NULL,
                value BLOB NOT NULL,
                owner_id TEXT NOT NULL DEFAULT 'system',
                key_version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (name, owner_id)
            )
        """))

    # Mock DB interface for secret store (uses _mapping for column-name access)
    class MockDB:
        def __init__(self, engine):
            self.engine = engine

        async def execute(self, query, params=None):
            from sqlalchemy import text
            async with self.engine.begin() as conn:
                await conn.execute(text(query), params or {})

        async def fetchone(self, query, params=None):
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                result = await conn.execute(text(query), params or {})
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None

        async def fetchall(self, query, params=None):
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                result = await conn.execute(text(query), params or {})
                return [dict(r._mapping) for r in result.fetchall()]

    # SECRET_KEY and JWT_SECRET are already set at module level
    # (see top of this file)

    mock_db = MockDB(db_engine)
    return SecretStore(mock_db)


@pytest_asyncio.fixture
async def state_store(db_engine):
    """Create execution state store."""
    class MockDB:
        def __init__(self, engine):
            self.engine = engine

        async def execute(self, query, params=None):
            from sqlalchemy import text
            async with self.engine.begin() as conn:
                if params:
                    if isinstance(params, dict):
                        # Use named params directly
                        result = await conn.execute(text(query), params)
                    elif isinstance(params, tuple):
                        # Replace ? placeholders with :p0, :p1, etc.
                        query_text = query
                        param_dict = {}
                        for i, val in enumerate(params):
                            param_name = f'p{i}'
                            param_dict[param_name] = val
                            query_text = query_text.replace('?', f':{param_name}', 1)
                        result = await conn.execute(text(query_text), param_dict)
                else:
                    result = await conn.execute(text(query))
                return result

        async def fetchone(self, query, params=None):
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                if params:
                    if isinstance(params, dict):
                        # Use named params directly
                        result = await conn.execute(text(query), params)
                    elif isinstance(params, tuple):
                        query_text = query
                        param_dict = {}
                        for i, val in enumerate(params):
                            param_name = f'p{i}'
                            param_dict[param_name] = val
                            query_text = query_text.replace('?', f':{param_name}', 1)
                        result = await conn.execute(text(query_text), param_dict)
                else:
                    result = await conn.execute(text(query))
                row = result.fetchone()
                if row:
                    return {"current_node": row[0], "context": row[1]}
                return None

    mock_db = MockDB(db_engine)
    return ExecutionStateStore(mock_db)


@pytest_asyncio.fixture
async def executor(mock_mcp_manager, secret_store, state_store):
    """Create workflow executor."""
    return WorkflowExecutor(
        mcp_manager=mock_mcp_manager,
        secret_store=secret_store,
        state_store=state_store,
    )


@pytest.fixture
def sample_workflow():
    """Create sample workflow with 5 nodes."""
    nodes = [
        WorkflowNode(
            id="node-1",
            type="agent",
            data={
                "name": "Input Parser",
                "role": "Parse input",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
            },
        ),
        WorkflowNode(
            id="node-2",
            type="mcp_tool",
            data={
                "serverId": "test-server",
                "toolName": "process_data",
                "parameters": {"input": "{{node-1.output}}"},
            },
        ),
        WorkflowNode(
            id="node-3",
            type="condition",
            data={
                "condition": "len(input) > 0",
            },
        ),
        WorkflowNode(
            id="node-4",
            type="agent",
            data={
                "name": "Formatter",
                "role": "Format output",
                "model": "gpt-4o-mini",
                "temperature": 0.5,
            },
        ),
        WorkflowNode(
            id="node-5",
            type="agent",
            data={
                "name": "Finalizer",
                "role": "Final output",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="edge-1", source="node-1", target="node-2"),
        WorkflowEdge(id="edge-2", source="node-2", target="node-3"),
        WorkflowEdge(id="edge-3", source="node-3", target="node-4"),
        WorkflowEdge(id="edge-4", source="node-4", target="node-5"),
    ]

    return Workflow(
        id=str(uuid.uuid4()),
        name="Test Workflow",
        nodes=nodes,
        edges=edges,
        description="A test workflow with 5 nodes",
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )


@pytest.fixture
def simple_workflow():
    """Create simple 2-node workflow for quick tests."""
    nodes = [
        WorkflowNode(
            id="start",
            type="agent",
            data={
                "name": "Start Agent",
                "role": "Process input",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="end",
            type="agent",
            data={
                "name": "End Agent",
                "role": "Finalize",
                "model": "gpt-4o-mini",
            },
        ),
    ]

    edges = [
        WorkflowEdge(id="edge-1", source="start", target="end"),
    ]

    return Workflow(
        id=str(uuid.uuid4()),
        name="Simple Workflow",
        nodes=nodes,
        edges=edges,
        description="Simple 2-node workflow",
    )


# Factory functions for creating test data (no hardcoded mock data)
def create_workflow(
    workflow_id: str | None = None,
    name: str = "Test Workflow",
    node_count: int = 2,
) -> Workflow:
    """Factory function to create workflow for testing.

    Args:
        workflow_id: Optional workflow ID (generates UUID if not provided)
        name: Workflow name
        node_count: Number of nodes to create

    Returns:
        Workflow instance
    """
    nodes = []
    edges = []

    for i in range(node_count):
        node_id = f"node-{i+1}"
        nodes.append(
            WorkflowNode(
                id=node_id,
                type="agent",
                data={
                    "name": f"Agent {i+1}",
                    "role": f"Process step {i+1}",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                },
            )
        )

        # Connect nodes sequentially
        if i > 0:
            edges.append(
                WorkflowEdge(
                    id=f"edge-{i}",
                    source=f"node-{i}",
                    target=node_id,
                )
            )

    return Workflow(
        id=workflow_id or str(uuid.uuid4()),
        name=name,
        nodes=nodes,
        edges=edges,
        description=f"Test workflow with {node_count} nodes",
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )


def create_schedule(
    workflow_id: str | None = None,
    expression: str = "0 9 * * *",
    timezone: str = "UTC",
    enabled: bool = True,
) -> dict:
    """Factory function to create schedule data for testing.

    Args:
        workflow_id: Workflow ID to schedule
        expression: Cron expression
        timezone: Schedule timezone
        enabled: Whether schedule is enabled

    Returns:
        Dictionary with schedule data
    """
    return {
        "workflow_id": workflow_id or str(uuid.uuid4()),
        "expression": expression,
        "timezone": timezone,
        "enabled": enabled,
        "input": {},
    }


def create_execution(
    workflow_id: str | None = None,
    status: str = "pending",
    trigger_type: str = "manual",
) -> dict:
    """Factory function to create execution data for testing.

    Args:
        workflow_id: Workflow ID to execute
        status: Execution status
        trigger_type: How execution was triggered

    Returns:
        Dictionary with execution data
    """
    return {
        "id": str(uuid.uuid4()),
        "workflow_id": workflow_id or str(uuid.uuid4()),
        "status": status,
        "trigger_type": trigger_type,
        "input": "test input",
        "started_at": datetime.now(UTC).replace(tzinfo=None),
    }
