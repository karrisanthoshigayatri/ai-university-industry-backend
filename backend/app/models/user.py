"""User database model."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


USER_ROLES = (
    "Citizen",
    "Government Officer",
    "HEI Administrator",
    "Faculty / Expert",
    "Student",
    "Industry / MSME / Startup",
    "Research Institution",
    "CSR Organization",
    "System Administrator",
)


class User(Base):
    """A platform user belonging to one organization."""

    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        CheckConstraint(
            "role IN ('Citizen', 'Government Officer', 'HEI Administrator', 'Faculty / Expert', 'Student', 'Industry / MSME / Startup', 'Research Institution', 'CSR Organization', 'System Administrator')",
            name="ck_user_role",
        ),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_user_status"),
        Index("ix_user_organization_id", "organization_id"),
        Index("ix_user_role", "role"),
        Index("ix_user_status", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization.organization_id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="users")
    problems: Mapped[list["Problem"]] = relationship(  # type: ignore[name-defined]
        foreign_keys="Problem.submitter_id", back_populates="submitter"
    )
    evidence_submitted: Mapped[list["ProblemEvidence"]] = relationship(  # type: ignore[name-defined]
        foreign_keys="ProblemEvidence.submitted_by", back_populates="submitter"
    )
    validations: Mapped[list["Validation"]] = relationship(  # type: ignore[name-defined]
        foreign_keys="Validation.validator_id", back_populates="validator"
    )