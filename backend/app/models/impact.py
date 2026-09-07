"""ImpactRecord, Beneficiary, Feedback models — Step 23.

Column types match Supabase exactly:
  impact_record.location   → JSONB
  impact_record.verified_by → FK app_user (no FK in our mapper, raw UUID)
  beneficiary.location     → JSONB
  beneficiary.estimated_count → BIGINT
  feedback.submitted_by    → FK app_user (raw UUID)
  feedback.submitted_at    → TIMESTAMP (no tz)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImpactRecord(Base):
    __tablename__ = "impact_record"
    __table_args__ = (Index("ix_impact_project_id", "project_id"),)

    impact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    metric: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    achieved_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    # raw UUID — FK to app_user not mapped to avoid metadata error
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Beneficiary(Base):
    __tablename__ = "beneficiary"
    __table_args__ = (Index("ix_beneficiary_project_id", "project_id"),)

    beneficiary_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    beneficiary_type: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estimated_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    affected_domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_project_id", "project_id"),)

    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=True)
    problem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("problem.problem_id", ondelete="CASCADE"), nullable=True)
    # raw UUID — FK to app_user
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    feedback_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
