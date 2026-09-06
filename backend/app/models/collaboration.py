"""CollaborationRequest and ProjectPartner models — Step 21.

DB column notes:
  collaboration_request.sent_at      → maps to requested_at (Python attr)
  collaboration_request.request_type → maps to contribution_type (Python attr)
  Missing in DB: requested_by, response_message — added via migration patch
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COLLAB_STATUSES = ("Requested", "Accepted", "Rejected", "Negotiating", "Closed")
PARTNER_STATUSES = ("Active", "Completed", "Withdrawn")


class CollaborationRequest(Base):
    """A request from a project to collaborate with a partner."""

    __tablename__ = "collaboration_request"
    __table_args__ = (
        Index("ix_collab_project_id", "project_id"),
        Index("ix_collab_partner_id", "partner_id"),
        Index("ix_collab_status", "status"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("partner_profile.partner_id", ondelete="CASCADE"), nullable=False)
    # DB col = request_type, spec calls it contribution_type
    contribution_type: Mapped[str | None] = mapped_column("request_type", Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Requested", server_default="Requested")
    # DB col = sent_at, spec calls it requested_at
    requested_at: Mapped[datetime | None] = mapped_column("sent_at", DateTime(timezone=False), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    # Added via migration
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProjectPartner(Base):
    """An active partnership between a project and a partner organisation."""

    __tablename__ = "project_partner"
    __table_args__ = (
        UniqueConstraint("project_id", "partner_id", name="uq_project_partner"),
        Index("ix_proj_partner_project_id", "project_id"),
        Index("ix_proj_partner_partner_id", "partner_id"),
    )

    project_partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("partner_profile.partner_id", ondelete="RESTRICT"), nullable=False)
    contribution_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    contribution_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Active", server_default="Active")
