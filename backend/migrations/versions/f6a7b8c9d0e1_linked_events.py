"""linked events: event_links table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-12 16:50:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: str | None = 'e5f6a7b8c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'event_links',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('event_a_id', sa.String(length=32), nullable=False),
        sa.Column('event_b_id', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_a_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_b_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_a_id', 'event_b_id', name='uq_event_link_pair'),
    )
    with op.batch_alter_table('event_links', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_event_links_event_a_id'), ['event_a_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_event_links_event_b_id'), ['event_b_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('event_links', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_event_links_event_b_id'))
        batch_op.drop_index(batch_op.f('ix_event_links_event_a_id'))
    op.drop_table('event_links')
