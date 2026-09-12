"""ORM models. See the plan in .claude/plans for the schema rationale.

Tables for later milestones (google_connections, processed_emails, scan_runs,
application_events) are declared now so a single initial migration creates the
whole shape and later milestones only add columns/logic.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in tests).
JsonB = JSON().with_variant(JSONB(), "postgresql")
# Native uuid on Postgres, CHAR(32) elsewhere.
UuidType = Uuid(as_uuid=True)


class Base(DeclarativeBase):
    pass


def _uuid_col() -> Mapped[uuid.UUID]:
    return mapped_column(UuidType, primary_key=True, default=uuid.uuid4)


class ApplicationStatus(str, enum.Enum):
    saved = "saved"
    applied = "applied"
    in_progress = "in_progress"
    interview = "interview"
    accepted = "accepted"
    rejected = "rejected"


# Rough forward-progress ordering; used to decide whether an incoming signal is "newer".
# accepted/rejected are both terminal (same rank) so a correction between them still applies.
STATUS_RANK = {
    ApplicationStatus.saved: 0,
    ApplicationStatus.applied: 1,
    ApplicationStatus.in_progress: 2,
    ApplicationStatus.interview: 3,
    ApplicationStatus.accepted: 4,
    ApplicationStatus.rejected: 4,
}

STATUS_LABELS = {
    ApplicationStatus.saved: "Saved",
    ApplicationStatus.applied: "Applied",
    ApplicationStatus.in_progress: "In Progress",
    ApplicationStatus.interview: "Interview",
    ApplicationStatus.accepted: "Accepted",
    ApplicationStatus.rejected: "Rejected",
}

PLATFORM_LABELS = {
    "linkedin": "LinkedIn",
    "jobstreet": "JobStreet",
    "seek": "SEEK",
    "indeed": "Indeed",
    "glassdoor": "Glassdoor",
    "lever": "Lever",
    "greenhouse": "Greenhouse",
    "ashby": "Ashby",
    "generic": "Other",
}


class ApplicationSource(str, enum.Enum):
    manual = "manual"
    email = "email"
    link = "link"


class EventType(str, enum.Enum):
    applied = "applied"
    assessment = "assessment"
    interview = "interview"
    rejection = "rejection"
    offer = "offer"
    status_update = "status_update"
    other = "other"


# Used to auto-log a timeline event when upsert_application() changes status
# but the caller didn't supply one explicitly (e.g. the agent's chat tool).
STATUS_TO_EVENT_TYPE = {
    ApplicationStatus.saved: EventType.other,
    ApplicationStatus.applied: EventType.applied,
    ApplicationStatus.in_progress: EventType.assessment,
    ApplicationStatus.interview: EventType.interview,
    ApplicationStatus.accepted: EventType.offer,
    ApplicationStatus.rejected: EventType.rejection,
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_col()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    credential: Mapped[UserCredential | None] = relationship(back_populates="user", uselist=False)


class UserCredential(Base):
    __tablename__ = "user_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="credential")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_platform: Mapped[str | None] = mapped_column(String(40))
    raw_text: Mapped[str | None] = mapped_column(Text)

    company: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(80))
    seniority: Mapped[str | None] = mapped_column(String(80))
    remote_policy: Mapped[str | None] = mapped_column(String(80))
    salary_text: Mapped[str | None] = mapped_column(String(255))

    skills: Mapped[list[str]] = mapped_column(JsonB, default=list)
    experience_requirements: Mapped[list[str]] = mapped_column(JsonB, default=list)
    education_requirements: Mapped[list[str]] = mapped_column(JsonB, default=list)
    summary: Mapped[str | None] = mapped_column(Text)

    model: Mapped[str | None] = mapped_column(String(80))
    token_usage: Mapped[dict] = mapped_column(JsonB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_application_user_dedupe"),)

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_posting_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_postings.id", ondelete="SET NULL"))

    company: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(255))
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.saved
    )
    status_confidence: Mapped[float | None] = mapped_column(Float)
    source: Mapped[ApplicationSource] = mapped_column(
        Enum(ApplicationSource, name="application_source"), default=ApplicationSource.manual
    )
    next_action: Mapped[str | None] = mapped_column(Text)
    next_action_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sheet_row: Mapped[int | None] = mapped_column(Integer)

    # Denormalized from the linked JobPosting at tracking time (email-sourced or
    # manually-tracked applications with no posting simply leave these null).
    salary: Mapped[str | None] = mapped_column(String(255))
    requirements: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str | None] = mapped_column(String(40))

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # When the *current* status began — distinct from last_update_at, which
    # bumps on any field edit (next_action, salary, ...) and would otherwise
    # be shown next to the status pill looking like "the date it was rejected"
    # when it might just be an unrelated edit.
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="ApplicationEvent.occurred_at"
    )


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = _uuid_col()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    summary: Mapped[str | None] = mapped_column(Text)
    raw_snippet: Mapped[str | None] = mapped_column(Text)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="events")


class GoogleConnection(Base):
    __tablename__ = "google_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(Text)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str | None] = mapped_column(Text)
    google_email: Mapped[str | None] = mapped_column(String(320))
    spreadsheet_id: Mapped[str | None] = mapped_column(String(255))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"
    __table_args__ = (UniqueConstraint("user_id", "gmail_message_id", name="uq_processed_email"),)

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    classification: Mapped[str | None] = mapped_column(String(40))
    application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("applications.id", ondelete="SET NULL"))


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    messages_scanned: Mapped[int] = mapped_column(Integer, default=0)
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    applications_updated: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    rolling_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = _uuid_col()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant | tool
    content: Mapped[str] = mapped_column(Text, default="")
    tool_calls: Mapped[dict | None] = mapped_column(JsonB)
    tool_call_id: Mapped[str | None] = mapped_column(String(80))
    # Python-side default: each row gets a distinct microsecond timestamp so
    # messages in one turn keep their insertion order (the DB's now() is
    # constant within a transaction and would scramble them).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
