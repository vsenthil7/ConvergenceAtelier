"""session mode and media urls

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-12 11:40:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SESSION_MODE = sa.Enum('IN_PERSON', 'ONLINE', 'HYBRID', name='sessionmode')


def upgrade() -> None:
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'mode',
                SESSION_MODE,
                nullable=False,
                server_default='IN_PERSON',
            )
        )
        batch_op.add_column(
            sa.Column('stream_url', sa.String(length=500), nullable=False, server_default='')
        )
        batch_op.add_column(
            sa.Column('meeting_url', sa.String(length=500), nullable=False, server_default='')
        )
        batch_op.add_column(
            sa.Column('recording_url', sa.String(length=500), nullable=False, server_default='')
        )


def downgrade() -> None:
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_column('recording_url')
        batch_op.drop_column('meeting_url')
        batch_op.drop_column('stream_url')
        batch_op.drop_column('mode')
