"""Organization database model."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


ORGANIZATION_TYPES = (
    "Government",
    "PRI",
    "ULB",
    "HEI",
    "Industry",
    "MSME",
    "Startup",
    "Research Institution",
    "CSR Organization",
)


class Organization(Base):
    """An organization participating in the platform."""

    __tablename__ = "organization"
    __table_args__ = (
        UniqueConstraint("official_identifier", name="uq_organization_official_identifier"),
        CheckConstraint(
            "organization_type IN ('Government', 'PRI', 'ULB', 'HEI', 'Industry', 'MSME', 'Startup', 'Research Institution', 'CSR Organization')",
            name="ck_organization_type",
        ),
        Index("ix_organization_name", "name"),
        Index("ix_organization_type", "organization_type"),
        Index("ix_organization_location", "state", "district"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(50), nullable=False)
    official_identifier: Mapped[str | None] = mapped_column(String(150), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    contact_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="Pending", server_default="Pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    government_profile: Mapped["GovernmentProfile | None"] = relationship(
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )
    hei_profile: Mapped["HeiProfile | None"] = relationship(  # type: ignore[name-defined]
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )