"""add execution states table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-02-12 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create execution_states table for ExecutionStateStore
    op.create_table(
        'execution_states',
        sa.Column('execution_id', sa.String(length=36), nullable=False),
        sa.Column('current_node', sa.String(length=255), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='running'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('execution_id')
    )


def downgrade() -> None:
    # Drop execution_states table
    op.drop_table('execution_states')
