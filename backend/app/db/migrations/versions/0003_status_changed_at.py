"""applications.status_changed_at

Revision ID: 0003_status_changed_at
Revises: 0002_application_fields
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_status_changed_at"
down_revision: Union[str, None] = "0002_application_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("status_changed_at", sa.DateTime(timezone=True)))
    # Backfill: best guess for existing rows is "when we first saw it".
    op.execute("UPDATE applications SET status_changed_at = first_seen_at WHERE status_changed_at IS NULL")


def downgrade() -> None:
    op.drop_column("applications", "status_changed_at")
