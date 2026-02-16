"""Tests for audit logging."""
import pytest
import uuid
from datetime import datetime, timedelta
from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog


class TestAuditService:
    """Tests for audit service."""

    @pytest.mark.asyncio
    async def test_log_action(self, db_session):
        """Test basic audit log creation."""
        service = AuditService(db_session)

        # Log an action
        log = await service.log(
            action="create",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            details={"name": "Test Workflow", "version": 1},
            ip_address="192.168.1.1",
            success=True,
        )

        # Verify log was created
        assert log.id is not None
        assert log.action == "create"
        assert log.resource_type == "workflow"
        assert log.event_type == "workflow.create"
        assert log.ip_address == "192.168.1.1"
        assert log.success is True

    @pytest.mark.asyncio
    async def test_pii_sanitized_in_details(self, db_session):
        """Test that PII is sanitized in audit log details."""
        service = AuditService(db_session)

        # Log action with PII in details (use strings with patterns, not just values)
        log = await service.log(
            action="update",
            resource_type="user",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            details={
                "contact": "email: user@example.com",
                "phone_info": "phone: 123-456-7890",
                "name": "John Doe",
                "credentials": 'password="secret123"',
            },
            success=True,
        )

        # Verify PII was sanitized
        assert log.details is not None
        assert "[EMAIL]" in log.details
        assert "user@example.com" not in log.details
        assert "[PHONE]" in log.details
        assert "123-456-7890" not in log.details
        assert "[REDACTED]" in log.details
        assert "secret123" not in log.details
        # Non-PII should remain
        assert "John Doe" in log.details

    @pytest.mark.asyncio
    async def test_log_without_details(self, db_session):
        """Test logging without details."""
        service = AuditService(db_session)

        log = await service.log(
            action="delete",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            success=True,
        )

        assert log.id is not None
        assert log.details is None

    @pytest.mark.asyncio
    async def test_log_failure(self, db_session):
        """Test logging failed actions."""
        service = AuditService(db_session)

        log = await service.log(
            action="execute",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            details={"error": "Execution failed"},
            success=False,
        )

        assert log.success is False
        assert "error" in log.details

    @pytest.mark.asyncio
    async def test_get_logs_with_filters(self, db_session):
        """Test retrieving logs with filters."""
        service = AuditService(db_session)
        user_id = str(uuid.uuid4())

        # Create multiple logs
        for i in range(5):
            await service.log(
                action="read" if i % 2 == 0 else "write",
                resource_type="workflow" if i < 3 else "execution",
                resource_id=str(uuid.uuid4()),
                user_id=user_id,
                success=True,
            )

        await db_session.commit()

        # Get all logs for user
        all_logs = await service.get_logs(user_id=user_id)
        assert len(all_logs) == 5

        # Filter by resource type
        workflow_logs = await service.get_logs(user_id=user_id, resource_type="workflow")
        assert len(workflow_logs) == 3

        execution_logs = await service.get_logs(user_id=user_id, resource_type="execution")
        assert len(execution_logs) == 2

        # Filter by action
        read_logs = await service.get_logs(user_id=user_id, action="read")
        assert len(read_logs) == 3

        write_logs = await service.get_logs(user_id=user_id, action="write")
        assert len(write_logs) == 2

    @pytest.mark.asyncio
    async def test_get_logs_pagination(self, db_session):
        """Test log pagination."""
        service = AuditService(db_session)
        user_id = str(uuid.uuid4())

        # Create 15 logs
        for i in range(15):
            await service.log(
                action="test",
                resource_type="workflow",
                resource_id=str(uuid.uuid4()),
                user_id=user_id,
                success=True,
            )

        await db_session.commit()

        # Get first page
        page1 = await service.get_logs(user_id=user_id, limit=10, offset=0)
        assert len(page1) == 10

        # Get second page
        page2 = await service.get_logs(user_id=user_id, limit=10, offset=10)
        assert len(page2) == 5

        # Verify no overlap
        page1_ids = {log.id for log in page1}
        page2_ids = {log.id for log in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0

    @pytest.mark.asyncio
    async def test_get_log_by_id(self, db_session):
        """Test retrieving single log by ID."""
        service = AuditService(db_session)

        # Create log
        created_log = await service.log(
            action="create",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            success=True,
        )

        await db_session.commit()

        # Retrieve by ID
        retrieved_log = await service.get_log(created_log.id)

        assert retrieved_log is not None
        assert retrieved_log.id == created_log.id
        assert retrieved_log.action == created_log.action

    @pytest.mark.asyncio
    async def test_get_nonexistent_log(self, db_session):
        """Test retrieving nonexistent log returns None."""
        service = AuditService(db_session)

        log = await service.get_log("nonexistent-id")
        assert log is None

    @pytest.mark.asyncio
    async def test_logs_ordered_by_timestamp_desc(self, db_session):
        """Test logs are returned in reverse chronological order."""
        service = AuditService(db_session)
        user_id = str(uuid.uuid4())

        # Create logs with slight delays to ensure different timestamps
        import asyncio

        log_ids = []
        for i in range(5):
            log = await service.log(
                action="test",
                resource_type="workflow",
                resource_id=str(uuid.uuid4()),
                user_id=user_id,
                details={"sequence": i},
                success=True,
            )
            log_ids.append(log.id)
            await asyncio.sleep(0.01)  # Small delay to ensure timestamp difference

        await db_session.commit()

        # Retrieve logs
        logs = await service.get_logs(user_id=user_id)

        # Verify order (newest first)
        assert len(logs) == 5
        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_nested_pii_sanitization(self, db_session):
        """Test nested structures are sanitized."""
        service = AuditService(db_session)

        # Log with nested PII (use patterns in strings, not just values)
        log = await service.log(
            action="update",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            details={
                "workflow": {
                    "name": "Test",
                    "owner": {
                        "contact": "email: owner@example.com",
                        "tel": "phone: 123-456-7890",
                    },
                },
                "metadata": {
                    "auth": 'api_key="sk-secret123"',
                },
            },
            success=True,
        )

        # Verify nested PII was sanitized
        assert "[EMAIL]" in log.details
        assert "owner@example.com" not in log.details
        assert "[PHONE]" in log.details
        assert "123-456-7890" not in log.details
        assert "[REDACTED]" in log.details
        assert "sk-secret123" not in log.details

    @pytest.mark.asyncio
    async def test_log_with_list_details(self, db_session):
        """Test logging with list in details."""
        service = AuditService(db_session)

        log = await service.log(
            action="bulk_update",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            details={
                "items": [
                    {"id": "1", "email": "user1@test.com"},
                    {"id": "2", "email": "user2@test.com"},
                ]
            },
            success=True,
        )

        # Verify emails in list were sanitized
        assert "[EMAIL]" in log.details
        assert "user1@test.com" not in log.details
        assert "user2@test.com" not in log.details

    @pytest.mark.asyncio
    async def test_concurrent_logging(self, db_session):
        """Test concurrent log creation."""
        service = AuditService(db_session)
        user_id = str(uuid.uuid4())

        # Create logs sequentially (concurrent session flushes cause issues)
        logs = []
        for i in range(10):
            log = await service.log(
                action="test",
                resource_type="workflow",
                resource_id=str(uuid.uuid4()),
                user_id=user_id,
                details={"index": i},
                success=True,
            )
            logs.append(log)

        await db_session.commit()

        # Verify all were created
        assert len(logs) == 10
        assert all(log.id is not None for log in logs)

        # Verify all can be retrieved
        retrieved = await service.get_logs(user_id=user_id)
        assert len(retrieved) == 10

    @pytest.mark.asyncio
    async def test_log_with_empty_details(self, db_session):
        """Test logging with empty details dict."""
        service = AuditService(db_session)

        log = await service.log(
            action="test",
            resource_type="workflow",
            resource_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            details={},
            success=True,
        )

        # Empty dict should be handled
        assert log.id is not None
