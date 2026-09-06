"""AI analysis SQLAlchemy models.

Four tables that store structured Qwen2.5 output:
- ProblemCategory      — domain categories extracted from the problem
- ProblemPriority      — priority/severity scoring
- ProblemRequirementProfile  — high-level support requirements
- ProblemRequirementCapability — granular capability requirements
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


CATEGORY_ROLES = ("Primary", "Secondary")

PRIORITY_LEVELS = ("Low", "Medium", "High", "Critical")

REQUIREMENT_TYPES = (
    "Domain",
    "Skill",
    "Expertise",
    "Technology",
    "Resource",
    "Support Capability",
)


class ProblemCategory(Base):
    """AI-generated domain category linked to a canonical Capability."""

    __tablename__ = "problem_category"
    __table_args__ = (
        CheckConstraint(
            "category_role IN ('Primary', 'Secondary')",
            name="ck_problem_category_role",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_problem_category_confidence",
        ),
        Index("ix_problem_category_problem_id", "problem_id"),
        Index("ix_problem_category_capability_id", "capability_id"),
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    capability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability.capability_id", ondelete="SET NULL"),
        nullable=True,
    )
    category_role: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship(  # type: ignore[name-defined]
        back_populates="categories"
    )


class ProblemPriority(Base):
    """AI-generated priority and severity scoring for a problem."""

    __tablename__ = "problem_priority"
    __table_args__ = (
        CheckConstraint(
            "priority_level IN ('Low', 'Medium', 'High', 'Critical')",
            name="ck_problem_priority_level",
        ),
        Index("ix_problem_priority_problem_id", "problem_id"),
        Index("ix_problem_priority_level", "priority_level"),
    )

    priority_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    priority_level: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    urgency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    affected_population: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    geographic_spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    feasibility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    strategic_relevance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship(  # type: ignore[name-defined]
        back_populates="priorities"
    )


class ProblemRequirementProfile(Base):
    """High-level support requirements extracted from a problem by AI."""

    __tablename__ = "problem_requirement_profile"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_req_profile_confidence",
        ),
        Index("ix_req_profile_problem_id", "problem_id"),
    )

    requirement_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    required_support: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship(  # type: ignore[name-defined]
        back_populates="requirement_profiles"
    )
    capability_requirements: Mapped[list["ProblemRequirementCapability"]] = relationship(
        back_populates="requirement_profile", cascade="all, delete-orphan"
    )


class ProblemRequirementCapability(Base):
    """Granular capability requirements linked to a requirement profile."""

    __tablename__ = "problem_requirement_capability"
    __table_args__ = (
        CheckConstraint(
            "requirement_type IN ("
            "'Domain','Skill','Expertise','Technology','Resource','Support Capability')",
            name="ck_req_capability_type",
        ),
        Index("ix_req_capability_profile_id", "requirement_profile_id"),
        Index("ix_req_capability_capability_id", "capability_id"),
    )

    requirement_capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requirement_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem_requirement_profile.requirement_profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    capability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability.capability_id", ondelete="SET NULL"),
        nullable=True,
    )
    requirement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    criticality: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    requirement_profile: Mapped["ProblemRequirementProfile"] = relationship(
        back_populates="capability_requirements"
    )
