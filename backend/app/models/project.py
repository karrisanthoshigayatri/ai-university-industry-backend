"""Project, ProjectTeam, ProjectTeamMember, ProjectResource, ProjectCapability models.

All tables already exist in Supabase. Column names and types match exactly.
Notes:
- project.project_lead → FK to app_user (not user)
- project_team_member.user_id → FK to app_user (not user)
- project status values: Proposed/Active/On Hold/Completed/Cancelled
- project stage values: Proposal/Development/Prototype/Testing/Pilot/Deployment/Completed
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PROJECT_STATUSES = ("Proposed", "Active", "On Hold", "Completed", "Cancelled")
PROJECT_STAGES = (
    "Proposal", "Development", "Prototype",
    "Testing", "Pilot", "Deployment", "Completed",
)
MEMBER_TYPES = ("Faculty", "Student", "Expert")
MEMBER_STATUSES = ("Active", "Inactive")
TEAM_STATUSES = ("Active", "Inactive", "Completed")
RESOURCE_ACCESS_STATUSES = ("Requested", "Approved", "Active", "Returned", "Rejected")


class Project(Base):
    """A project linking a problem to an HEI."""

    __tablename__ = "project"
    __table_args__ = (
        Index("ix_project_problem_id", "problem_id"),
        Index("ix_project_hei_id", "hei_id"),
        Index("ix_project_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("problem.problem_id", ondelete="RESTRICT"), nullable=False)
    hei_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hei_profile.hei_id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Proposed", server_default="Proposed")
    current_stage: Mapped[str] = mapped_column(Text, nullable=False, default="Proposal", server_default="Proposal")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # FK → user table (note: Supabase has app_user but our app uses 'user')
    project_lead: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())

    team: Mapped[list["ProjectTeam"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    resources: Mapped[list["ProjectResource"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    capabilities: Mapped[list["ProjectCapability"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectTeam(Base):
    """Team attached to a project."""

    __tablename__ = "project_team"
    __table_args__ = (
        Index("ix_team_project_id", "project_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    hei_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hei_profile.hei_id", ondelete="CASCADE"), nullable=False)
    faculty_lead: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("faculty_expert_profile.faculty_expert_id", ondelete="SET NULL"), nullable=True)
    formation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True, default="Active", server_default="Active")

    project: Mapped["Project"] = relationship(back_populates="team")
    members: Mapped[list["ProjectTeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class ProjectTeamMember(Base):
    """Individual member of a project team."""

    __tablename__ = "project_team_member"
    __table_args__ = (
        Index("ix_team_member_team_id", "team_id"),
        Index("ix_team_member_user_id", "user_id"),
    )

    team_member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project_team.team_id", ondelete="CASCADE"), nullable=False)
    # FK → user table (note: Supabase has app_user but our app uses 'user')
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    member_type: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(Text, nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True, default="Active", server_default="Active")

    team: Mapped["ProjectTeam"] = relationship(back_populates="members")


class ProjectResource(Base):
    """Institutional resource allocated to a project."""

    __tablename__ = "project_resource"
    __table_args__ = (
        Index("ix_proj_res_project_id", "project_id"),
        Index("ix_proj_res_resource_id", "resource_id"),
    )

    project_resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("institutional_resource.resource_id", ondelete="RESTRICT"), nullable=False)
    usage: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_status: Mapped[str | None] = mapped_column(Text, nullable=True, default="Requested", server_default="Requested")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="resources")


class ProjectCapability(Base):
    """Capability contributed to or used by a project."""

    __tablename__ = "project_capability"
    __table_args__ = (
        Index("ix_proj_cap_project_id", "project_id"),
        Index("ix_proj_cap_capability_id", "capability_id"),
    )

    project_capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability.capability_id", ondelete="RESTRICT"), nullable=False)
    source_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    strength_level: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("capability_evidence.evidence_id", ondelete="SET NULL"), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="capabilities")
