"""add_composite_indexes

Revision ID: 855d6a3cbef6
Revises: e2f3a4b5c6d7
Create Date: 2026-02-15 01:38:36.718883
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '855d6a3cbef6'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Audit logs indexes for user activity and action filtering
    op.create_index(
        "ix_audit_logs_user_timestamp",
        "audit_logs",
        ["user_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_action_timestamp",
        "audit_logs",
        ["action", "timestamp"],
        unique=False,
    )

    # Executions indexes for workflow listing and status filtering
    op.create_index(
        "ix_executions_workflow_status",
        "executions",
        ["workflow_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_executions_workflow_started",
        "executions",
        ["workflow_id", "started_at"],
        unique=False,
    )

    # A/B test results index for statistics aggregation
    op.create_index(
        "ix_ab_test_results_test_variant_created",
        "ab_test_results",
        ["test_id", "variant", "created_at"],
        unique=False,
    )

    # Webhooks index for active webhook lookup
    op.create_index(
        "ix_webhooks_workflow_enabled",
        "webhooks",
        ["workflow_id", "enabled"],
        unique=False,
    )

    # Schedules indexes for workflow lookup and enabled schedule queries
    op.create_index(
        "ix_schedules_workflow_enabled",
        "schedules",
        ["workflow_id", "enabled"],
        unique=False,
    )
    op.create_index(
        "ix_schedules_enabled_created",
        "schedules",
        ["enabled", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index("ix_schedules_enabled_created", table_name="schedules")
    op.drop_index("ix_schedules_workflow_enabled", table_name="schedules")
    op.drop_index("ix_webhooks_workflow_enabled", table_name="webhooks")
    op.drop_index("ix_ab_test_results_test_variant_created", table_name="ab_test_results")
    op.drop_index("ix_executions_workflow_started", table_name="executions")
    op.drop_index("ix_executions_workflow_status", table_name="executions")
    op.drop_index("ix_audit_logs_action_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_timestamp", table_name="audit_logs")
