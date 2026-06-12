"""event registrations

Revision ID: a1b2c3d4e5f6
Revises: 260b0661c707
Create Date: 2026-06-12 09:05:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '260b0661c707'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'event_registrations',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('event_id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column(
            'status',
            sa.Enum('REGISTERED', 'CANCELLED', name='registrationstatus'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'user_id', name='uq_event_user'),
    )
    with op.batch_alter_table('event_registrations', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_event_registrations_event_id'), ['event_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_event_registrations_user_id'), ['user_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('event_registrations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_event_registrations_user_id'))
        batch_op.drop_index(batch_op.f('ix_event_registrations_event_id'))
    op.drop_table('event_registrations')
