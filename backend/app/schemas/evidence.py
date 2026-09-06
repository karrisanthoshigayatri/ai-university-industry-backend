"""Pydantic schemas for CapabilityEvidence, Availability, and EntityConstraint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Shared literals ────────────────────────────────────────────────────────────

EntityType = Literal[
    "hei_capability",
    "faculty_expertise",
    "institutional_resource",
    "partner_capability",
]

EvidenceType = Literal[
    "Certification",
    "Publication",
    "Project",
    "Patent",
    "Laboratory",
    "Infrastructure",
    "Experience",
    "Official Document",
    "Website",
]

VerificationStatus = Literal["Pending", "Verified", "Rejected"]

AvailabilityStatusType = Literal[
    "Available",
    "Partially Available",
    "Unavailable",
    "On Leave",
]

SeverityLevel = Literal["Low", "Medium", "High", "Critical"]


# ══════════════════════════════════════════════════════════════════════════════
# CapabilityEvidence
# ══════════════════════════════════════════════════════════════════════════════

class EvidenceCreate(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    capability_id: UUID | None = None
    evidence_type: EvidenceType
    source: str | None = Field(default=None, max_length=500)
    reference: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    # recency is stored as a date in DB
    recency: date | None = None
    verification_status: VerificationStatus = "Pending"


class EvidenceUpdate(BaseModel):
    evidence_type: EvidenceType | None = None
    source: str | None = Field(default=None, max_length=500)
    reference: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    recency: date | None = None
    verification_status: VerificationStatus | None = None


class EvidenceVerify(BaseModel):
    """Payload used by Government Officers to verify evidence.

    verified_by and verified_at are NOT accepted from the client —
    they are injected server-side from the authenticated user/session.
    """
    verification_status: VerificationStatus


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: UUID
    entity_type: str
    entity_id: UUID
    capability_id: UUID | None
    evidence_type: str
    source: str | None
    reference: str | None
    description: str | None
    recency: date | None
    verified_by: UUID | None
    verified_at: datetime | None
    verification_status: str
    created_at: datetime
    updated_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# Availability
# ══════════════════════════════════════════════════════════════════════════════

class AvailabilityCreate(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    status: AvailabilityStatusType = "Available"
    capacity: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    # conditions stored as text in DB
    conditions: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "AvailabilityCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class AvailabilityUpdate(BaseModel):
    status: AvailabilityStatusType | None = None
    capacity: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    conditions: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "AvailabilityUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    availability_id: UUID
    entity_type: str
    entity_id: UUID
    status: str
    capacity: int | None
    start_date: date | None
    end_date: date | None
    conditions: str | None
    created_at: datetime
    updated_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# EntityConstraint
# ══════════════════════════════════════════════════════════════════════════════

class ConstraintCreate(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    constraint_type: str = Field(min_length=1, max_length=100)
    value: str | None = None
    severity: SeverityLevel = "Medium"
    validity_period: dict | None = None


class ConstraintUpdate(BaseModel):
    constraint_type: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = None
    severity: SeverityLevel | None = None
    validity_period: dict | None = None


class ConstraintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    constraint_id: UUID
    entity_type: str
    entity_id: UUID
    constraint_type: str
    value: str | None
    severity: str
    validity_period: dict | None
    created_at: datetime
    updated_at: datetime
