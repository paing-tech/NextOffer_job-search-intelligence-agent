"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

application_status = sa.Enum(
    "discovered", "applied", "assessment", "interview", "offer", "rejected", "withdrawn", "ghosted",
    name="application_status",
)
application_source = sa.Enum("manual", "email", "link", name="application_source")
event_type = sa.Enum(
    "applied", "assessment", "interview", "rejection", "offer", "status_update", "other", name="event_type"
)

JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_credentials",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )

    op.create_table(
        "job_postings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("source_platform", sa.String(40)),
        sa.Column("raw_text", sa.Text),
        sa.Column("company", sa.String(255)),
        sa.Column("title", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("employment_type", sa.String(80)),
        sa.Column("seniority", sa.String(80)),
        sa.Column("remote_policy", sa.String(80)),
        sa.Column("salary_text", sa.String(255)),
        sa.Column("skills", JSONB, nullable=False, server_default="[]"),
        sa.Column("experience_requirements", JSONB, nullable=False, server_default="[]"),
        sa.Column("education_requirements", JSONB, nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text),
        sa.Column("model", sa.String(80)),
        sa.Column("token_usage", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_postings_user_id", "job_postings", ["user_id"])

    op.create_table(
        "applications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_posting_id", UUID, sa.ForeignKey("job_postings.id", ondelete="SET NULL")),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(255), nullable=False),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column("status", application_status, nullable=False, server_default="discovered"),
        sa.Column("status_confidence", sa.Float),
        sa.Column("source", application_source, nullable=False, server_default="manual"),
        sa.Column("next_action", sa.Text),
        sa.Column("next_action_due", TS),
        sa.Column("sheet_row", sa.Integer),
        sa.Column("first_seen_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("last_update_at", TS, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_application_user_dedupe"),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_dedupe_key", "applications", ["dedupe_key"])

    op.create_table(
        "application_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("occurred_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("raw_snippet", sa.Text),
        sa.Column("gmail_message_id", sa.String(255)),
        sa.Column("gmail_thread_id", sa.String(255)),
        sa.Column("model", sa.String(80)),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_application_events_application_id", "application_events", ["application_id"])
    op.create_index("ix_application_events_gmail_message_id", "application_events", ["gmail_message_id"])

    op.create_table(
        "google_connections",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("encrypted_refresh_token", sa.Text),
        sa.Column("access_token", sa.Text),
        sa.Column("token_expiry", TS),
        sa.Column("scopes", sa.Text),
        sa.Column("google_email", sa.String(320)),
        sa.Column("spreadsheet_id", sa.String(255)),
        sa.Column("connected_at", TS, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "processed_emails",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=False),
        sa.Column("processed_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("classification", sa.String(40)),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.UniqueConstraint("user_id", "gmail_message_id", name="uq_processed_email"),
    )
    op.create_index("ix_processed_emails_user_id", "processed_emails", ["user_id"])

    op.create_table(
        "scan_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", TS),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("messages_scanned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("events_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("applications_updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text),
    )
    op.create_index("ix_scan_runs_user_id", "scan_runs", ["user_id"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("rolling_summary", sa.Text),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("session_id", UUID, sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("tool_calls", JSONB),
        sa.Column("tool_call_id", sa.String(80)),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    for table in (
        "chat_messages", "chat_sessions", "scan_runs", "processed_emails", "google_connections",
        "application_events", "applications", "job_postings", "user_credentials", "users",
    ):
        op.drop_table(table)
    event_type.drop(op.get_bind(), checkfirst=True)
    application_source.drop(op.get_bind(), checkfirst=True)
    application_status.drop(op.get_bind(), checkfirst=True)
