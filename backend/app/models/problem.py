"""Problem and ProblemEvidence database models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


SOURCE_TYPES = (
    "Citizen",
    "Community",
    "PRI",
    "ULB",
    "Government",
)

PROBLEM_STATUSES = (
    "Submitted",
    "Similar Found",
    "Pending Validation",
    "Validated",
    "Rejected",
    "Redirected",
    "Linked to Existing Problem",
    "Matched",
    "Accepted",
    "Active",
    "Completed",
)

EVIDENCE_TYPES = (
    "Photograph",
    "Video",
    "Document",
    "Geo-location",
    "Government record",
    "Citizen report",
)

EVIDENCE_VERIFICATION_STATUSES = (
    "Pending",
    "Verified",
    "Rejected",
)


class Problem(Base):
    """A problem submitted by a platform user."""

    __tablename__ = "problem"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('Citizen', 'Community', 'PRI', 'ULB', 'Government')",
            name="ck_problem_source_type",
        ),
        CheckConstraint(
            "current_status IN ("
            "'Submitted', 'Similar Found', 'Pending Validation', 'Validated', "
            "'Rejected', 'Redirected', 'Linked to Existing Problem', "
            "'Matched', 'Accepted', 'Active', 'Completed')",
            name="ck_problem_current_status",
        ),
        Index("ix_problem_submitter_id", "submitter_id"),
        Index("ix_problem_current_status", "current_status"),
        Index("ix_problem_source_type", "source_type"),
        Index("ix_problem_submission_date", "submission_date"),
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    submitter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submission_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    current_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Submitted",
        server_default="Submitted",
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

    submitter: Mapped["User"] = relationship(back_populates="problems")  # type: ignore[name-defined]
    evidence: Mapped[list["ProblemEvidence"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )
    # Relations where this problem is the source
    relations_as_source: Mapped[list["ProblemRelation"]] = relationship(
        foreign_keys="ProblemRelation.source_problem_id",
        back_populates="source_problem",
        cascade="all, delete-orphan",
    )
    # Relations where this problem is the target
    relations_as_target: Mapped[list["ProblemRelation"]] = relationship(
        foreign_keys="ProblemRelation.target_problem_id",
        back_populates="target_problem",
        cascade="all, delete-orphan",
    )
    # Validation history
    validations: Mapped[list["ProblemRelation"]] = relationship(  # type: ignore[name-defined]
        "Validation", back_populates="problem", cascade="all, delete-orphan"
    )


class ProblemEvidence(Base):
    """Evidence attached to a problem submission."""

    __tablename__ = "problem_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ("
            "'Photograph', 'Video', 'Document', 'Geo-location', "
            "'Government record', 'Citizen report')",
            name="ck_evidence_type",
        ),
        CheckConstraint(
            "verification_status IN ('Pending', 'Verified', 'Rejected')",
            name="ck_evidence_verification_status",
        ),
        Index("ix_problem_evidence_problem_id", "problem_id"),
        Index("ix_problem_evidence_submitted_by", "submitted_by"),
        Index("ix_problem_evidence_verification_status", "verification_status"),
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Pending",
        server_default="Pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    problem: Mapped["Problem"] = relationship(back_populates="evidence")
    submitter: Mapped["User"] = relationship(  # type: ignore[name-defined]
        foreign_keys=[submitted_by], back_populates="evidence_submitted"
    )


RELATION_TYPES = (
    "Similar",
    "Duplicate",
    "Related",
    "Consolidated",
    "Linked",
)


class ProblemRelation(Base):
    """AI-generated or human-confirmed relationship between two problems.

    The AI may only create 'Similar' relations (human_confirmation=False).
    A Government Officer or System Administrator must confirm any final
    Duplicate / Consolidated / Linked decision.
    """

    __tablename__ = "problem_relation"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('Similar', 'Duplicate', 'Related', 'Consolidated', 'Linked')",
            name="ck_problem_relation_type",
        ),
        CheckConstraint(
            "source_problem_id <> target_problem_id",
            name="ck_problem_relation_no_self",
        ),
        Index("ix_problem_relation_source", "source_problem_id"),
        Index("ix_problem_relation_target", "target_problem_id"),
        Index("ix_problem_relation_type", "relation_type"),
        Index("ix_problem_relation_human_confirmation", "human_confirmation"),
    )

    relation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False, default="Similar")
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # False = AI recommendation not yet confirmed; True = human confirmed/rejected
    human_confirmation: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source_problem: Mapped["Problem"] = relationship(
        foreign_keys=[source_problem_id], back_populates="relations_as_source"
    )
    target_problem: Mapped["Problem"] = relationship(
        foreign_keys=[target_problem_id], back_populates="relations_as_target"
    )
    decider: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        foreign_keys=[decided_by]
    )
