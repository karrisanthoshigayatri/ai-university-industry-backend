"""Faculty / Resource contextual match model — Step 15.

Maps to the existing Supabase faculty_resource_match table.
Missing columns (match_type, unmet_requirements, constraint_results, created_at)
are added via the 20260906_fr_match migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

FR_MODEL_VERSION = "faculty-resource-matching-v1"
MATCH_TYPES = ("Faculty", "Resource")


class FacultyResourceMatch(Base):
    """Snapshot of a faculty or resource recommendation for a problem."""

    __tablename__ = "faculty_resource_match"
    __table_args__ = (
        Index("ix_fr_match_problem_id", "problem_id"),
        Index("ix_fr_match_hei_id", "hei_id"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    hei_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hei_profile.hei_id", ondelete="CASCADE"),
        nullable=False,
    )
    # DB column name is faculty_expert_id
    faculty_id: Mapped[uuid.UUID | None] = mapped_column(
        "faculty_expert_id",
        UUID(as_uuid=True),
        ForeignKey("faculty_expert_profile.faculty_expert_id", ondelete="SET NULL"),
        nullable=True,
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutional_resource.resource_id", ondelete="SET NULL"),
        nullable=True,
    )
    match_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    match_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    matched_capabilities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unmet_requirements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    constraint_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # DB column is 'reasons'; Python attr is match_reasons
    match_reasons: Mapped[list | None] = mapped_column("reasons", JSONB, nullable=True)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DB generated_at is TIMESTAMP (no tz)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
