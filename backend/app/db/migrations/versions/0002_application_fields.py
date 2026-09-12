"""application status set + salary/requirements/platform columns

Revision ID: 0002_application_fields
Revises: 0001_initial
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_application_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_TO_NEW = {
    "discovered": "saved",
    "applied": "applied",
    "assessment": "in_progress",
    "interview": "interview",
    "offer": "accepted",
    "rejected": "rejected",
    "withdrawn": "rejected",
    "ghosted": "rejected",
}
_NEW_TO_OLD = {
    "saved": "discovered",
    "applied": "applied",
    "in_progress": "assessment",
    "interview": "interview",
    "accepted": "offer",
    "rejected": "rejected",
}


def upgrade() -> None:
    op.add_column("applications", sa.Column("salary", sa.String(255)))
    op.add_column("applications", sa.Column("requirements", sa.Text()))
    op.add_column("applications", sa.Column("platform", sa.String(40)))

    op.execute("ALTER TYPE application_status RENAME TO application_status_old")
    op.execute(
        "CREATE TYPE application_status AS ENUM "
        "('saved','applied','in_progress','interview','accepted','rejected')"
    )
    op.execute("ALTER TABLE applications ALTER COLUMN status DROP DEFAULT")
    case_sql = " ".join(f"WHEN '{old}' THEN '{new}'" for old, new in _OLD_TO_NEW.items())
    op.execute(
        f"ALTER TABLE applications ALTER COLUMN status TYPE application_status "
        f"USING (CASE status::text {case_sql} END)::application_status"
    )
    op.execute("ALTER TABLE applications ALTER COLUMN status SET DEFAULT 'saved'")
    op.execute("DROP TYPE application_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE application_status RENAME TO application_status_new")
    op.execute(
        "CREATE TYPE application_status AS ENUM "
        "('discovered','applied','assessment','interview','offer','rejected','withdrawn','ghosted')"
    )
    op.execute("ALTER TABLE applications ALTER COLUMN status DROP DEFAULT")
    case_sql = " ".join(f"WHEN '{new}' THEN '{old}'" for new, old in _NEW_TO_OLD.items())
    op.execute(
        f"ALTER TABLE applications ALTER COLUMN status TYPE application_status "
        f"USING (CASE status::text {case_sql} END)::application_status"
    )
    op.execute("ALTER TABLE applications ALTER COLUMN status SET DEFAULT 'discovered'")
    op.execute("DROP TYPE application_status_new")

    op.drop_column("applications", "platform")
    op.drop_column("applications", "requirements")
    op.drop_column("applications", "salary")
