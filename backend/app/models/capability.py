"""Minimal Capability model — reflects the existing capability table.

The full capability taxonomy is managed by a future step.
This stub is required so SQLAlchemy can resolve foreign key references
from ProblemCategory and ProblemRequirementCapability.
"""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Capability(Base):
    """Canonical capability entry (stub for FK resolution)."""

    __tablename__ = "capability"

    capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
