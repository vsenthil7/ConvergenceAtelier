"""event type and config

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-12 10:45:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EVENT_TYPE = sa.Enum(
    'CONFERENCE', 'HACKATHON', 'WEBINAR', 'MEETUP', 'WORKSHOP', 'HYBRID',
    name='eventtype',
)


def upgrade() -> None:
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'event_type',
                EVENT_TYPE,
                nullable=False,
                server_default='CONFERENCE',
            )
        )
        batch_op.add_column(
            sa.Column(
                'config',
                sa.JSON(),
                nullable=False,
                server_default='{}',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_column('config')
        batch_op.drop_column('event_type')
