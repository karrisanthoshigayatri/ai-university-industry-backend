"""CapabilityGap and PartnerMatch models — Steps 19–20."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PARTNER_MATCH_MODEL_VERSION = "partner-matching-v1"

GAP_STATUSES = ("Open", "Partially Filled", "Filled", "Closed")
MATCH_DECISION_STATUSES = ("Recommended", "Under Review", "Accepted", "Rejected")


class CapabilityGap(Base):
    """Capability gap record for a project."""

    __tablename__ = "capability_gap"
    __table_args__ = (
        Index("ix_cap_gap_project_id", "project_id"),
        Index("ix_cap_gap_capability_id", "capability_id"),
    )

    gap_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability.capability_id", ondelete="RESTRICT"), nullable=False)
    required_level: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    available_level: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    gap_level: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    criticality: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    recommended_support: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Open", server_default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PartnerMatch(Base):
    """Partner matching snapshot for a project."""

    __tablename__ = "partner_match"
    __table_args__ = (
        Index("ix_partner_match_project_id", "project_id"),
        Index("ix_partner_match_partner_id", "partner_id"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("partner_profile.partner_id", ondelete="CASCADE"), nullable=False)
    match_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_capabilities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # DB column is matched_support; Python attr is support_matches
    support_matches: Mapped[list | None] = mapped_column("matched_support", JSONB, nullable=True)
    unmet_requirements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    constraint_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    match_reasons: Mapped[list | None] = mapped_column("reasons", JSONB, nullable=True)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
