"""HEI registry Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VerificationStatus = Literal["Pending", "Verified", "Rejected"]
ProficiencyLevel   = Literal["Beginner", "Intermediate", "Advanced", "Expert"]
CapabilityStatus   = Literal["Active", "Inactive"]
AvailabilityStatus = Literal["Available", "Partially Available", "Unavailable"]


# ── HEI Profile ────────────────────────────────────────────────────────────────

class HeiCreate(BaseModel):
    organization_id: UUID
    institution_type: str | None = Field(default=None, max_length=100)
    accreditation: str | None = None
    established_year: int | None = Field(default=None, ge=1000, le=2100)
    website: str | None = Field(default=None, max_length=500)
    contact_details: dict | None = None
    description: str | None = None
    verification_status: VerificationStatus = "Pending"


class HeiUpdate(BaseModel):
    institution_type: str | None = Field(default=None, max_length=100)
    accreditation: str | None = None
    established_year: int | None = Field(default=None, ge=1000, le=2100)
    website: str | None = Field(default=None, max_length=500)
    contact_details: dict | None = None
    description: str | None = None
    verification_status: VerificationStatus | None = None


class HeiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hei_id: UUID
    organization_id: UUID
    institution_type: str | None
    accreditation: str | None
    established_year: int | None
    website: str | None
    contact_details: dict | None
    description: str | None
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime


# ── HEI Capability ─────────────────────────────────────────────────────────────

class HeiCapabilityCreate(BaseModel):
    capability_id: UUID
    proficiency_level: ProficiencyLevel | None = None
    evidence_description: str | None = None
    status: CapabilityStatus = "Active"


class HeiCapabilityUpdate(BaseModel):
    proficiency_level: ProficiencyLevel | None = None
    evidence_description: str | None = None
    status: CapabilityStatus | None = None


class HeiCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hei_capability_id: UUID
    hei_id: UUID
    capability_id: UUID
    proficiency_level: str | None
    evidence_description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# ── Faculty Expert Profile ─────────────────────────────────────────────────────

class FacultyCreate(BaseModel):
    user_id: UUID | None = None
    designation: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    specialization: str | None = None
    experience_years: int | None = Field(default=None, ge=0)
    profile_description: str | None = None
    verification_status: VerificationStatus = "Pending"


class FacultyUpdate(BaseModel):
    designation: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    specialization: str | None = None
    experience_years: int | None = Field(default=None, ge=0)
    profile_description: str | None = None
    verification_status: VerificationStatus | None = None


class FacultyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    faculty_id: UUID
    hei_id: UUID
    user_id: UUID | None
    designation: str | None
    department: str | None
    specialization: str | None
    experience_years: int | None
    profile_description: str | None
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime


# ── Faculty Capability ─────────────────────────────────────────────────────────

class FacultyCapabilityCreate(BaseModel):
    capability_id: UUID
    proficiency_level: ProficiencyLevel | None = None
    evidence_description: str | None = None
    status: CapabilityStatus = "Active"


class FacultyCapabilityUpdate(BaseModel):
    proficiency_level: ProficiencyLevel | None = None
    evidence_description: str | None = None
    status: CapabilityStatus | None = None


class FacultyCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    faculty_capability_id: UUID
    faculty_id: UUID
    capability_id: UUID
    proficiency_level: str | None
    evidence_description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# ── Institutional Resource ─────────────────────────────────────────────────────

class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    resource_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    location: str | dict | None = Field(default=None)
    capacity: int | None = Field(default=None, ge=0)
    availability_status: AvailabilityStatus = "Available"
    verification_status: VerificationStatus = "Pending"


class ResourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    resource_type: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    location: str | dict | None = Field(default=None)
    capacity: int | None = Field(default=None, ge=0)
    availability_status: AvailabilityStatus | None = None
    verification_status: VerificationStatus | None = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    resource_id: UUID
    hei_id: UUID
    name: str
    resource_type: str
    description: str | None
    location: str | dict | None
    capacity: int | None
    availability_status: str
    verification_status: str
    created_at: datetime
    updated_at: datetime


# ── Resource Capability ────────────────────────────────────────────────────────

class ResourceCapabilityCreate(BaseModel):
    capability_id: UUID
    proficiency_level: ProficiencyLevel | None = None
    evidence_description: str | None = None
    status: CapabilityStatus = "Active"


class ResourceCapabilityUpdate(BaseModel):
    proficiency_level: ProficiencyLevel | None = None
    evidence_description: str | None = None
    status: CapabilityStatus | None = None


class ResourceCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    resource_capability_id: UUID
    resource_id: UUID
    capability_id: UUID
    proficiency_level: str | None
    evidence_description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
