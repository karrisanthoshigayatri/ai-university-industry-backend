"""External Partner Registry models.

Column names and types align with the existing Supabase schema.
Missing columns are added via the 20260906_partner_registry migration.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


PARTNER_TYPES = (
    "Industry",
    "MSME",
    "Startup",
    "Research Institution",
    "CSR Organization",
)

SUPPORT_TYPES = (
    "Funding",
    "Technology",
    "Mentorship",
    "Testing",
    "Manufacturing",
    "Deployment",
    "Infrastructure",
    "Market Access",
    "Domain Expertise",
)

VERIFICATION_STATUSES = ("Pending", "Verified", "Rejected")
OFFERING_STATUSES = ("Active", "Inactive", "Expired")
PROFICIENCY_LEVELS = (1, 2, 3, 4)


class PartnerProfile(Base):
    """One partner profile per organisation (Industry/MSME/Startup/etc.)."""

    __tablename__ = "partner_profile"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_partner_organization_id"),
        Index("ix_partner_org_id", "organization_id"),
        Index("ix_partner_type", "partner_type"),
        Index("ix_partner_verification", "verification_status"),
    )

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.organization_id", ondelete="CASCADE"),
        nullable=False,
    )
    partner_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="Pending", server_default="Pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        back_populates="partner_profile"
    )
    capabilities: Mapped[list["PartnerCapability"]] = relationship(
        back_populates="partner", cascade="all, delete-orphan"
    )
    offerings: Mapped[list["PartnerSupportOffering"]] = relationship(
        back_populates="partner", cascade="all, delete-orphan"
    )


class PartnerCapability(Base):
    """Partner ↔ canonical Capability link."""

    __tablename__ = "partner_capability"
    __table_args__ = (
        UniqueConstraint("partner_id", "capability_id", name="uq_partner_capability"),
        Index("ix_partner_cap_partner_id", "partner_id"),
        Index("ix_partner_cap_capability_id", "capability_id"),
    )

    partner_capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_profile.partner_id", ondelete="CASCADE"),
        nullable=False,
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability.capability_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # DB has strength_level as NUMERIC(5,2); proficiency_level added as integer
    strength_level: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    proficiency_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="Pending", server_default="Pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    partner: Mapped["PartnerProfile"] = relationship(back_populates="capabilities")
    capability: Mapped["Capability"] = relationship()  # type: ignore[name-defined]


class PartnerSupportOffering(Base):
    """A support offering made by a partner organisation."""

    __tablename__ = "partner_support_offering"
    __table_args__ = (
        Index("ix_offering_partner_id", "partner_id"),
        Index("ix_offering_support_type", "support_type"),
        Index("ix_offering_status", "status"),
    )

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partner_profile.partner_id", ondelete="CASCADE"),
        nullable=False,
    )
    support_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DB uses JSONB for capacity (Supabase legacy)
    capacity: Mapped[int | None] = mapped_column(JSONB, nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    availability_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    availability_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Active", server_default="Active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    partner: Mapped["PartnerProfile"] = relationship(back_populates="offerings")
