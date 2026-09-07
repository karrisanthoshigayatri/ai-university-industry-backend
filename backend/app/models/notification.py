"""Notification model — Step 24.

notification.recipient_id → FK to app_user (raw UUID, no mapped FK).
notification.created_at / read_at → TIMESTAMP (no tz).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

NOTIFICATION_STATUSES = ("Unread", "Read", "Archived")
EVENT_TYPES = (
    "submission_status", "duplicate_suggestion", "validation_request",
    "university_invitation", "partner_request", "milestone_update",
    "citizen_feedback", "project_completion",
)


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_recipient_id", "recipient_id"),
        Index("ix_notification_status", "status"),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # raw UUID — FK to app_user (not mapped to avoid metadata clash)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Unread", server_default="Unread")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
