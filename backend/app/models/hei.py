"""HEI (Higher Education Institution) registry models.

Column names match the existing Supabase schema exactly.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HeiProfile(Base):
    """University/College profile — one per HEI organization."""

    __tablename__ = "hei_profile"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_hei_profile_organization_id"),
        Index("ix_hei_profile_org_id", "organization_id"),
        Index("ix_hei_profile_verification", "verification_status"),
    )

    hei_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization.organization_id", ondelete="CASCADE"), nullable=False
    )
    institution_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    accreditation: Mapped[str | None] = mapped_column(Text, nullable=True)
    established_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending", server_default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="hei_profile")  # type: ignore[name-defined]
    capabilities: Mapped[list["HeiCapability"]] = relationship(back_populates="hei", cascade="all, delete-orphan")
    faculty: Mapped[list["FacultyExpertProfile"]] = relationship(back_populates="hei", cascade="all, delete-orphan")
    resources: Mapped[list["InstitutionalResource"]] = relationship(back_populates="hei", cascade="all, delete-orphan")


class HeiCapability(Base):
    """HEI ↔ canonical Capability link."""

    __tablename__ = "hei_capability"
    __table_args__ = (
        UniqueConstraint("hei_id", "capability_id", name="uq_hei_capability"),
        Index("ix_hei_capability_hei_id", "hei_id"),
        Index("ix_hei_capability_capability_id", "capability_id"),
    )

    hei_capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hei_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hei_profile.hei_id", ondelete="CASCADE"), nullable=False)
    capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability.capability_id", ondelete="RESTRICT"), nullable=False)
    proficiency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active", server_default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hei: Mapped["HeiProfile"] = relationship(back_populates="capabilities")
    capability: Mapped["Capability"] = relationship()  # type: ignore[name-defined]


class FacultyExpertProfile(Base):
    """Faculty member affiliated with an HEI."""

    __tablename__ = "faculty_expert_profile"
    __table_args__ = (
        Index("ix_faculty_hei_id", "hei_id"),
        Index("ix_faculty_user_id", "user_id"),
    )

    # DB uses faculty_expert_id as the real PK column name
    faculty_id: Mapped[uuid.UUID] = mapped_column("faculty_expert_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hei_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hei_profile.hei_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    specialization: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending", server_default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hei: Mapped["HeiProfile"] = relationship(back_populates="faculty")
    user: Mapped["User | None"] = relationship()  # type: ignore[name-defined]
    capabilities: Mapped[list["FacultyExpertCapability"]] = relationship(back_populates="faculty", cascade="all, delete-orphan")


class FacultyExpertCapability(Base):
    """Faculty expert ↔ canonical Capability link."""

    __tablename__ = "faculty_expert_capability"
    __table_args__ = (
        UniqueConstraint("faculty_expert_id", "capability_id", name="uq_faculty_capability"),
        Index("ix_faculty_cap_faculty_id", "faculty_expert_id"),
        Index("ix_faculty_cap_capability_id", "capability_id"),
    )

    faculty_capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # DB column is faculty_expert_id — map to faculty_id attribute
    faculty_id: Mapped[uuid.UUID] = mapped_column("faculty_expert_id", UUID(as_uuid=True), ForeignKey("faculty_expert_profile.faculty_expert_id", ondelete="CASCADE"), nullable=False)
    capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability.capability_id", ondelete="RESTRICT"), nullable=False)
    proficiency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active", server_default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    faculty: Mapped["FacultyExpertProfile"] = relationship(back_populates="capabilities")
    capability: Mapped["Capability"] = relationship()  # type: ignore[name-defined]


class InstitutionalResource(Base):
    """Lab or facility owned by an HEI."""

    __tablename__ = "institutional_resource"
    __table_args__ = (
        Index("ix_resource_hei_id", "hei_id"),
        Index("ix_resource_type", "resource_type"),
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hei_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hei_profile.hei_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DB stores location and capacity as JSONB (Supabase legacy schema)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    capacity: Mapped[int | None] = mapped_column(JSONB, nullable=True)
    availability_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Available", server_default="Available")
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending", server_default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hei: Mapped["HeiProfile"] = relationship(back_populates="resources")
    capabilities: Mapped[list["ResourceCapability"]] = relationship(back_populates="resource", cascade="all, delete-orphan")


class ResourceCapability(Base):
    """Resource ↔ canonical Capability link."""

    __tablename__ = "resource_capability"
    __table_args__ = (
        UniqueConstraint("resource_id", "capability_id", name="uq_resource_capability"),
        Index("ix_resource_cap_resource_id", "resource_id"),
        Index("ix_resource_cap_capability_id", "capability_id"),
    )

    resource_capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("institutional_resource.resource_id", ondelete="CASCADE"), nullable=False)
    capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability.capability_id", ondelete="RESTRICT"), nullable=False)
    proficiency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active", server_default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    resource: Mapped["InstitutionalResource"] = relationship(back_populates="capabilities")
    capability: Mapped["Capability"] = relationship()  # type: ignore[name-defined]
