"""Capability Evidence, Availability, and Constraint models.

All three use a polymorphic (entity_type, entity_id) pattern so a single
table supports multiple entity kinds without separate tables per entity.

Column types match the existing Supabase schema exactly.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ── Allowed entity types ───────────────────────────────────────────────────────

ENTITY_TYPES = (
    "hei_capability",
    "faculty_expertise",
    "institutional_resource",
    "partner_capability",
)

EVIDENCE_TYPES = (
    "Certification",
    "Publication",
    "Project",
    "Patent",
    "Laboratory",
    "Infrastructure",
    "Experience",
    "Official Document",
    "Website",
)

VERIFICATION_STATUSES = ("Pending", "Verified", "Rejected")
SEVERITY_LEVELS = ("Low", "Medium", "High", "Critical")


class CapabilityEvidence(Base):
    """Evidence record for any capability-holding entity (polymorphic).

    DB column types:
      entity_type, evidence_type, source, reference, description -> text
      recency -> date
      verification_status -> text
      capability_id, entity_id, verified_by -> uuid (nullable)
      created_at, updated_at -> timestamptz (added via migration patch)
    """

    __tablename__ = "capability_evidence"
    __table_args__ = (
        Index("ix_evidence_entity_type", "entity_type"),
        Index("ix_evidence_entity_id", "entity_id"),
        Index("ix_evidence_capability_id", "capability_id"),
        Index("ix_evidence_verification_status", "verification_status"),
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    capability_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DB column is date type
    recency: Mapped[date | None] = mapped_column(Date, nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="Pending", server_default="Pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Availability(Base):
    """Availability window for any entity (polymorphic).

    DB column types:
      entity_type, status -> text
      capacity -> jsonb (Supabase legacy)
      conditions -> text
      start_date, end_date -> date
      created_at, updated_at -> timestamptz (added via migration patch)
    """

    __tablename__ = "availability"
    __table_args__ = (
        Index("ix_availability_entity_type", "entity_type"),
        Index("ix_availability_entity_id", "entity_id"),
    )

    availability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="Available", server_default="Available"
    )
    # DB uses JSONB for capacity (Supabase legacy schema)
    capacity: Mapped[int | None] = mapped_column(JSONB, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # DB uses text for conditions
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EntityConstraint(Base):
    """Constraint attached to any entity (polymorphic).

    Named EntityConstraint to avoid collision with SQL reserved word 'Constraint'.
    DB column types match Supabase exactly — all varchar/text/jsonb.
    """

    __tablename__ = "entity_constraint"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('Low','Medium','High','Critical')",
            name="ck_constraint_severity",
        ),
        Index("ix_constraint_entity_type", "entity_type"),
        Index("ix_constraint_entity_id", "entity_id"),
    )

    constraint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    constraint_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Medium", server_default="Medium"
    )
    validity_period: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
