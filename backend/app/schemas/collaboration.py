"""Pydantic schemas for CollaborationRequest and ProjectPartner."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


CollabStatus = Literal["Requested", "Accepted", "Rejected", "Negotiating", "Closed"]
PartnerStatus = Literal["Active", "Completed", "Withdrawn"]


# ── Collaboration Request ──────────────────────────────────────────────────────

class CollabRequestCreate(BaseModel):
    partner_id: UUID
    contribution_type: str | None = None
    message: str | None = None


class CollabStatusUpdate(BaseModel):
    status: CollabStatus
    response_message: str | None = None


class CollabRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    request_id: UUID
    project_id: UUID
    partner_id: UUID
    requested_by: UUID | None
    contribution_type: str | None
    message: str | None
    status: str
    requested_at: datetime | None
    responded_at: datetime | None
    response_message: str | None
    created_at: datetime


# ── Project Partner ────────────────────────────────────────────────────────────

class ProjectPartnerCreate(BaseModel):
    partner_id: UUID
    contribution_type: str | None = None
    contribution_details: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: PartnerStatus = "Active"


class ProjectPartnerUpdate(BaseModel):
    contribution_type: str | None = None
    contribution_details: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: PartnerStatus | None = None


class ProjectPartnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_partner_id: UUID
    project_id: UUID
    partner_id: UUID
    contribution_type: str | None
    contribution_details: str | None
    start_date: date | None
    end_date: date | None
    status: str
