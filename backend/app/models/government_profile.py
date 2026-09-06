"""Government profile database model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GovernmentProfile(Base):
    """Government-specific profile linked one-to-one to an organization."""

    __tablename__ = "government_profile"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_government_profile_organization_id"),
        Index("ix_government_profile_administrative_level", "administrative_level"),
        Index("ix_government_profile_jurisdiction", "jurisdiction"),
    )

    government_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.organization_id", ondelete="CASCADE"),
        nullable=False,
    )
    department_name: Mapped[str] = mapped_column(String(255), nullable=False)
    administrative_level: Mapped[str] = mapped_column(String(50), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    nodal_officer: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="government_profile")