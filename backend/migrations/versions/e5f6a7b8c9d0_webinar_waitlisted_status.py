"""webinar: add WAITLISTED registration status

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-12 16:10:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = 'e5f6a7b8c9d0'
down_revision: str | None = 'd4e5f6a7b8c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    # Postgres stores the enum as a native type that must be extended explicitly.
    # SQLite stores it as VARCHAR, so the new value needs no DDL there.
    if bind.dialect.name == "postgresql":
        # ADD VALUE cannot run inside a transaction block on older PGs; commit first.
        op.execute("COMMIT")
        op.execute("ALTER TYPE registrationstatus ADD VALUE IF NOT EXISTS 'WAITLISTED'")


def downgrade() -> None:
    # Removing a value from a Postgres enum is unsafe/non-trivial and not required
    # for the demo; downgrade is a no-op. Existing WAITLISTED rows (if any) remain.
    pass
