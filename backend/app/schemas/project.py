"""Pydantic schemas for Project, ProjectTeam, ProjectTeamMember, ProjectResource, ProjectCapability."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProjectStatus = Literal["Proposed", "Active", "On Hold", "Completed", "Cancelled"]
ProjectStage = Literal["Proposal", "Development", "Prototype", "Testing", "Pilot", "Deployment", "Completed"]
MemberType = Literal["Faculty", "Student", "Expert"]
TeamStatus = Literal["Active", "Inactive", "Completed"]
MemberStatus = Literal["Active", "Inactive"]
ResourceAccessStatus = Literal["Requested", "Approved", "Active", "Returned", "Rejected"]


# ── Project ────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    problem_id: UUID
    hei_id: UUID
    title: str = Field(min_length=1)
    description: str | None = None
    objective: str | None = None
    solution_summary: str | None = None
    status: ProjectStatus = "Proposed"
    current_stage: ProjectStage = "Proposal"
    start_date: date | None = None
    expected_end_date: date | None = None
    project_lead: UUID | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    objective: str | None = None
    solution_summary: str | None = None
    start_date: date | None = None
    expected_end_date: date | None = None
    completion_date: date | None = None
    project_lead: UUID | None = None


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class ProjectStageUpdate(BaseModel):
    current_stage: ProjectStage


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: UUID
    problem_id: UUID
    hei_id: UUID
    title: str
    description: str | None
    objective: str | None
    solution_summary: str | None
    status: str
    current_stage: str
    start_date: date | None
    expected_end_date: date | None
    completion_date: date | None
    project_lead: UUID | None
    created_at: datetime
    updated_at: datetime


# ── Project Team ───────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    hei_id: UUID
    faculty_lead: UUID | None = None
    formation_date: date | None = None
    status: TeamStatus = "Active"


class TeamUpdate(BaseModel):
    faculty_lead: UUID | None = None
    formation_date: date | None = None
    status: TeamStatus | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    team_id: UUID
    project_id: UUID
    hei_id: UUID
    faculty_lead: UUID | None
    formation_date: date | None
    status: str | None


# ── Project Team Member ────────────────────────────────────────────────────────

class MemberCreate(BaseModel):
    user_id: UUID
    member_type: MemberType
    role: str | None = None
    status: MemberStatus = "Active"


class MemberUpdate(BaseModel):
    role: str | None = None
    status: MemberStatus | None = None
    left_at: datetime | None = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    team_member_id: UUID
    team_id: UUID
    user_id: UUID
    member_type: str
    role: str | None
    joined_at: datetime | None
    left_at: datetime | None
    status: str | None


# ── Project Resource ───────────────────────────────────────────────────────────

class ProjectResourceCreate(BaseModel):
    resource_id: UUID
    usage: str | None = None
    access_status: ResourceAccessStatus = "Requested"
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "ProjectResourceCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ProjectResourceUpdate(BaseModel):
    usage: str | None = None
    access_status: ResourceAccessStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_resource_id: UUID
    project_id: UUID
    resource_id: UUID
    usage: str | None
    access_status: str | None
    start_date: date | None
    end_date: date | None


# ── Project Capability ─────────────────────────────────────────────────────────

class ProjectCapabilityCreate(BaseModel):
    capability_id: UUID
    source_type: str | None = None
    source_id: UUID | None = None
    strength_level: float | None = Field(default=None, ge=0, le=10)
    evidence_id: UUID | None = None


class ProjectCapabilityUpdate(BaseModel):
    source_type: str | None = None
    source_id: UUID | None = None
    strength_level: float | None = Field(default=None, ge=0, le=10)
    evidence_id: UUID | None = None


class ProjectCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_capability_id: UUID
    project_id: UUID
    capability_id: UUID
    source_type: str | None
    source_id: UUID | None
    strength_level: float | None
    evidence_id: UUID | None
