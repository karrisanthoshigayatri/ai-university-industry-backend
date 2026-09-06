"""CapabilityTaxonomy and Capability Pydantic schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


CapabilityType = Literal[
    "Domain",
    "Skill",
    "Expertise",
    "Technology",
    "Resource",
    "Support Capability",
]

CapabilityStatus = Literal["Active", "Inactive", "Deprecated"]


# ── CapabilityTaxonomy ─────────────────────────────────────────────────────────

class TaxonomyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=100)
    parent_id: UUID | None = None
    synonyms: list[str] | None = None
    version: str | None = Field(default=None, max_length=50)
    active_status: bool = True


class TaxonomyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: UUID | None = None
    synonyms: list[str] | None = None
    version: str | None = Field(default=None, max_length=50)
    active_status: bool | None = None


class TaxonomyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    taxonomy_id: UUID
    name: str
    type: str
    parent_id: UUID | None
    synonyms: list[str] | None
    version: str | None
    active_status: bool


# ── Capability ─────────────────────────────────────────────────────────────────

class CapabilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    capability_type: CapabilityType
    taxonomy_id: UUID | None = None
    parent_capability_id: UUID | None = None
    description: str | None = None
    status: CapabilityStatus = "Active"


class CapabilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    capability_type: CapabilityType | None = None
    taxonomy_id: UUID | None = None
    parent_capability_id: UUID | None = None
    description: str | None = None
    status: CapabilityStatus | None = None


class CapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    capability_id: UUID
    taxonomy_id: UUID | None
    parent_capability_id: UUID | None
    name: str
    capability_type: CapabilityType
    description: str | None
    status: CapabilityStatus
