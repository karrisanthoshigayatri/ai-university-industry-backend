"""CapabilityTaxonomy and Capability SQLAlchemy models.

Hierarchy:
  CapabilityTaxonomy (e.g. "Engineering & Technology")
    └── Capability (e.g. "Water Management")
          └── child Capability (e.g. "Water Quality Monitoring")
"""

import uuid

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


CAPABILITY_TYPES = (
    "Domain",
    "Skill",
    "Expertise",
    "Technology",
    "Resource",
    "Support Capability",
)

CAPABILITY_STATUSES = ("Active", "Inactive", "Deprecated")


class CapabilityTaxonomy(Base):
    """Top-level grouping for capabilities (e.g. Engineering, Health, Agriculture)."""

    __tablename__ = "capability_taxonomy"
    __table_args__ = (
        UniqueConstraint("name", name="uq_capability_taxonomy_name"),
        Index("ix_capability_taxonomy_parent_id", "parent_id"),
        Index("ix_capability_taxonomy_active", "active_status"),
    )

    taxonomy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability_taxonomy.taxonomy_id", ondelete="SET NULL"),
        nullable=True,
    )
    synonyms: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    active_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Self-referential relationship
    parent: Mapped["CapabilityTaxonomy | None"] = relationship(
        "CapabilityTaxonomy",
        remote_side="CapabilityTaxonomy.taxonomy_id",
        back_populates="children",
    )
    children: Mapped[list["CapabilityTaxonomy"]] = relationship(
        "CapabilityTaxonomy",
        back_populates="parent",
    )
    capabilities: Mapped[list["Capability"]] = relationship(
        "Capability",
        back_populates="taxonomy",
        foreign_keys="Capability.taxonomy_id",
    )


class Capability(Base):
    """A canonical capability entry that can be linked to problems, HEIs, and partners."""

    __tablename__ = "capability"
    __table_args__ = (
        CheckConstraint(
            "capability_type IN ("
            "'Domain','Skill','Expertise','Technology','Resource','Support Capability')",
            name="ck_capability_type",
        ),
        CheckConstraint(
            "status IN ('Active','Inactive','Deprecated')",
            name="ck_capability_status",
        ),
        UniqueConstraint("name", "capability_type", name="uq_capability_name_type"),
        Index("ix_capability_taxonomy_id", "taxonomy_id"),
        Index("ix_capability_parent_id", "parent_capability_id"),
        Index("ix_capability_type", "capability_type"),
        Index("ix_capability_status", "status"),
    )

    capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    taxonomy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability_taxonomy.taxonomy_id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_capability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability.capability_id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    capability_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Active", server_default="Active"
    )

    # Relationships
    taxonomy: Mapped["CapabilityTaxonomy | None"] = relationship(
        "CapabilityTaxonomy",
        back_populates="capabilities",
        foreign_keys=[taxonomy_id],
    )
    parent: Mapped["Capability | None"] = relationship(
        "Capability",
        remote_side="Capability.capability_id",
        back_populates="children",
        foreign_keys=[parent_capability_id],
    )
    children: Mapped[list["Capability"]] = relationship(
        "Capability",
        back_populates="parent",
        foreign_keys="Capability.parent_capability_id",
    )
