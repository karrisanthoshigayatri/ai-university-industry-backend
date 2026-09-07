"""Pydantic schemas for ProjectMilestone and ProjectOutput."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MilestoneStatus = Literal["Pending", "In Progress", "Completed", "Delayed", "Cancelled"]
OutputType = Literal["Prototype", "Software", "Hardware", "Pilot", "Deployment",
                     "Publication", "Patent", "Startup"]


# ── Milestone ──────────────────────────────────────────────────────────────────

class MilestoneCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    stage: str | None = None
    due_date: date | None = None
    completion_date: date | None = None
    status: MilestoneStatus = "Pending"
    evidence: str | None = None
    remarks: str | None = None


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    stage: str | None = None
    due_date: date | None = None
    completion_date: date | None = None
    evidence: str | None = None
    remarks: str | None = None


class MilestoneStatusUpdate(BaseModel):
    status: MilestoneStatus
    completion_date: date | None = None
    remarks: str | None = None


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    milestone_id: UUID
    project_id: UUID
    name: str
    description: str | None
    stage: str | None
    due_date: date | None
    completion_date: date | None
    status: str
    evidence: str | None
    remarks: str | None
    created_at: datetime
    updated_at: datetime


# ── Output ─────────────────────────────────────────────────────────────────────

class OutputCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    output_type: OutputType
    title: str = Field(min_length=1)
    description: str | None = None
    evidence: str | None = None
    output_date: date | None = Field(default=None, alias="date")


class OutputUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    output_type: OutputType | None = None
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    evidence: str | None = None
    output_date: date | None = Field(default=None, alias="date")


class OutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    output_id: UUID
    project_id: UUID
    output_type: str
    title: str
    description: str | None
    evidence: str | None
    date: date | None
    created_at: datetime
    updated_at: datetime
