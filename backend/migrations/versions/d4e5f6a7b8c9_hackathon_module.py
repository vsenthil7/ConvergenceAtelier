"""hackathon module: teams, members, submissions, scores

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-12 13:50:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: str | None = 'c3d4e5f6a7b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SUBMISSION_STATUS = sa.Enum(
    'DRAFT', 'SUBMITTED', 'DISQUALIFIED', name='submissionstatus'
)


def upgrade() -> None:
    op.create_table(
        'teams',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('event_id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'name', name='uq_team_event_name'),
    )
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teams_event_id'), ['event_id'], unique=False)

    op.create_table(
        'team_members',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('team_id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member'),
    )
    with op.batch_alter_table('team_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_team_members_team_id'), ['team_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_team_members_user_id'), ['user_id'], unique=False)

    op.create_table(
        'submissions',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('team_id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('repo_url', sa.String(length=500), nullable=False),
        sa.Column('demo_url', sa.String(length=500), nullable=False),
        sa.Column('status', SUBMISSION_STATUS, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', name='uq_submission_team'),
    )
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_submissions_team_id'), ['team_id'], unique=False)

    op.create_table(
        'scores',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('submission_id', sa.String(length=32), nullable=False),
        sa.Column('judge_id', sa.String(length=32), nullable=False),
        sa.Column('criterion', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['judge_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'submission_id', 'judge_id', 'criterion', name='uq_score_judge_criterion'
        ),
    )
    with op.batch_alter_table('scores', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_scores_submission_id'), ['submission_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_scores_judge_id'), ['judge_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('scores', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_scores_judge_id'))
        batch_op.drop_index(batch_op.f('ix_scores_submission_id'))
    op.drop_table('scores')
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_submissions_team_id'))
    op.drop_table('submissions')
    with op.batch_alter_table('team_members', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_team_members_user_id'))
        batch_op.drop_index(batch_op.f('ix_team_members_team_id'))
    op.drop_table('team_members')
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_teams_event_id'))
    op.drop_table('teams')
