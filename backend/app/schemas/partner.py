"""Pydantic schemas for Partner Registry (Profile, Capability, SupportOffering)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Literals ───────────────────────────────────────────────────────────────────

PartnerType = Literal[
    "Industry",
    "MSME",
    "Startup",
    "Research Institution",
    "CSR Organization",
]

SupportType = Literal[
    "Funding",
    "Technology",
    "Mentorship",
    "Testing",
    "Manufacturing",
    "Deployment",
    "Infrastructure",
    "Market Access",
    "Domain Expertise",
]

VerificationStatus = Literal["Pending", "Verified", "Rejected"]
OfferingStatus = Literal["Active", "Inactive", "Expired"]
ProficiencyLevel = Literal[1, 2, 3, 4]


# ══════════════════════════════════════════════════════════════════════════════
# PartnerProfile
# ══════════════════════════════════════════════════════════════════════════════

class PartnerProfileCreate(BaseModel):
    organization_id: UUID
    partner_type: PartnerType
    description: str | None = None
    website: str | None = Field(default=None, max_length=500)
    contact_details: dict | None = None


class PartnerProfileUpdate(BaseModel):
    partner_type: PartnerType | None = None
    description: str | None = None
    website: str | None = Field(default=None, max_length=500)
    contact_details: dict | None = None


class PartnerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    partner_id: UUID
    organization_id: UUID
    partner_type: str
    description: str | None
    website: str | None
    contact_details: dict | None
    verification_status: str
    created_at: datetime
    updated_at: datetime


class PartnerVerifyRequest(BaseModel):
    """Only Government Officers / System Admins may submit this."""
    verification_status: VerificationStatus


# ══════════════════════════════════════════════════════════════════════════════
# PartnerCapability
# ══════════════════════════════════════════════════════════════════════════════

class PartnerCapabilityCreate(BaseModel):
    capability_id: UUID
    proficiency_level: ProficiencyLevel | None = None
    experience_description: str | None = None
    evidence_reference: str | None = None
    verification_status: VerificationStatus = "Pending"


class PartnerCapabilityUpdate(BaseModel):
    proficiency_level: ProficiencyLevel | None = None
    experience_description: str | None = None
    evidence_reference: str | None = None
    verification_status: VerificationStatus | None = None


class PartnerCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    partner_capability_id: UUID
    partner_id: UUID
    capability_id: UUID
    proficiency_level: int | None
    experience_description: str | None
    evidence_reference: str | None
    verification_status: str
    created_at: datetime
    updated_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# PartnerSupportOffering
# ══════════════════════════════════════════════════════════════════════════════

class PartnerSupportOfferingCreate(BaseModel):
    support_type: SupportType
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    eligibility: str | None = None
    availability_start: date | None = None
    availability_end: date | None = None
    location: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def end_after_start(self) -> "PartnerSupportOfferingCreate":
        if (
            self.availability_start
            and self.availability_end
            and self.availability_end < self.availability_start
        ):
            raise ValueError("availability_end cannot be before availability_start")
        return self


class PartnerSupportOfferingUpdate(BaseModel):
    support_type: SupportType | None = None
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    eligibility: str | None = None
    availability_start: date | None = None
    availability_end: date | None = None
    location: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    status: OfferingStatus | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "PartnerSupportOfferingUpdate":
        if (
            self.availability_start
            and self.availability_end
            and self.availability_end < self.availability_start
        ):
            raise ValueError("availability_end cannot be before availability_start")
        return self


class PartnerSupportOfferingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offering_id: UUID
    partner_id: UUID
    support_type: str
    title: str | None
    description: str | None
    capacity: int | None
    eligibility: str | None
    availability_start: date | None
    availability_end: date | None
    location: str | None
    estimated_value: float | None
    status: str
    created_at: datetime
    updated_at: datetime
