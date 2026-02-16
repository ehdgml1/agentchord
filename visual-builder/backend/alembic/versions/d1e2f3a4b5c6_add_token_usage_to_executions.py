"""add token usage to executions

Revision ID: d1e2f3a4b5c6
Revises: 7246be057f11
Create Date: 2026-02-11 17:11:18.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = '7246be057f11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add token usage tracking columns to executions table
    op.add_column('executions', sa.Column('total_tokens', sa.Integer(), nullable=True))
    op.add_column('executions', sa.Column('prompt_tokens', sa.Integer(), nullable=True))
    op.add_column('executions', sa.Column('completion_tokens', sa.Integer(), nullable=True))
    op.add_column('executions', sa.Column('estimated_cost', sa.Float(), nullable=True))
    op.add_column('executions', sa.Column('model_used', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove token usage tracking columns from executions table
    op.drop_column('executions', 'model_used')
    op.drop_column('executions', 'estimated_cost')
    op.drop_column('executions', 'completion_tokens')
    op.drop_column('executions', 'prompt_tokens')
    op.drop_column('executions', 'total_tokens')
