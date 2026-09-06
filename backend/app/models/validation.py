"""Validation database model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


VALIDATION_STATUSES = (
    "Valid Problem",
    "Invalid Problem",
    "Redirect",
    "More Information Required",
)


class Validation(Base):
    """A government officer's validation decision on a submitted problem.

    Multiple records are kept per problem to preserve the full audit history.
    Querying for the latest record (by validated_at) gives the current decision.
    """

    __tablename__ = "validation"
    __table_args__ = (
        CheckConstraint(
            "validation_status IN ("
            "'Valid Problem', 'Invalid Problem', "
            "'Redirect', 'More Information Required')",
            name="ck_validation_status",
        ),
        Index("ix_validation_problem_id", "problem_id"),
        Index("ix_validation_validator_id", "validator_id"),
        Index("ix_validation_validated_at", "validated_at"),
        Index("ix_validation_status", "validation_status"),
    )

    validation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    validator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    validation_status: Mapped[str] = mapped_column(String(40), nullable=False)
    field_verification_required: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False
    )
    field_visit_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_review: Mapped[str | None] = mapped_column(Text, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    problem: Mapped["Problem"] = relationship(  # type: ignore[name-defined]
        back_populates="validations"
    )
    validator: Mapped["User"] = relationship(  # type: ignore[name-defined]
        foreign_keys=[validator_id], back_populates="validations"
    )
