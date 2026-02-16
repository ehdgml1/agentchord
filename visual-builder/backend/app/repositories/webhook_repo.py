"""Webhook repository implementation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook


class WebhookRepository:
    """Webhook repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session.
        """
        self.session = session

    async def create(
        self,
        workflow_id: str,
        secret: str,
        allowed_ips: str | None = None,
        input_mapping: str | None = None,
    ) -> Webhook:
        """Create a new webhook.

        Args:
            workflow_id: ID of workflow to trigger.
            secret: HMAC secret for signature verification.
            allowed_ips: Comma-separated allowed IPs.
            input_mapping: JSON input mapping template.

        Returns:
            Created webhook entity.
        """
        webhook = Webhook(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            secret=secret,
            allowed_ips=allowed_ips,
            input_mapping=input_mapping,
            enabled=True,
            last_called_at=None,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.session.add(webhook)
        await self.session.flush()
        return webhook

    async def get_by_id(self, webhook_id: str) -> Webhook | None:
        """Get webhook by ID.

        Args:
            webhook_id: Webhook ID.

        Returns:
            Webhook entity or None if not found.
        """
        stmt = select(Webhook).where(Webhook.id == webhook_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Webhook]:
        """List all webhooks.

        Returns:
            List of all webhooks.
        """
        stmt = select(Webhook).order_by(Webhook.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_workflow(self, workflow_id: str) -> list[Webhook]:
        """List all webhooks for a workflow.

        Args:
            workflow_id: Workflow ID.

        Returns:
            List of webhooks for the workflow.
        """
        stmt = (
            select(Webhook)
            .where(Webhook.workflow_id == workflow_id)
            .order_by(Webhook.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, webhook_id: str) -> bool:
        """Delete a webhook.

        Args:
            webhook_id: Webhook ID.

        Returns:
            True if deleted, False if not found.
        """
        stmt = delete(Webhook).where(Webhook.id == webhook_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def rotate_secret(self, webhook_id: str, new_secret: str) -> Webhook | None:
        """Rotate webhook secret.

        Args:
            webhook_id: Webhook ID.
            new_secret: New HMAC secret.

        Returns:
            Updated webhook or None if not found.
        """
        webhook = await self.get_by_id(webhook_id)
        if not webhook:
            return None

        webhook.secret = new_secret
        await self.session.flush()
        return webhook

    async def update_last_called(
        self,
        webhook_id: str,
        timestamp: datetime,
    ) -> None:
        """Update last called timestamp.

        Args:
            webhook_id: Webhook ID.
            timestamp: Call timestamp.
        """
        stmt = (
            update(Webhook)
            .where(Webhook.id == webhook_id)
            .values(last_called_at=timestamp)
        )
        await self.session.execute(stmt)
