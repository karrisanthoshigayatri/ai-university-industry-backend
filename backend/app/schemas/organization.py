"""Organization API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


OrganizationType = Literal[
    "Government",
    "PRI",
    "ULB",
    "HEI",
    "Industry",
    "MSME",
    "Startup",
    "Research Institution",
    "CSR Organization",
]


class OrganizationFields(BaseModel):
    """Shared organization input fields."""

    name: str = Field(min_length=1, max_length=255)
    organization_type: OrganizationType
    official_identifier: str | None = Field(default=None, max_length=150)
    address: str | None = None
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    contact_details: dict[str, str] | None = None
    website: HttpUrl | None = None
    verification_status: str = Field(default="Pending", min_length=1, max_length=30)


class OrganizationCreate(OrganizationFields):
    """Payload for creating an organization."""


class OrganizationUpdate(BaseModel):
    """Payload for partially updating an organization."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    organization_type: OrganizationType | None = None
    official_identifier: str | None = Field(default=None, max_length=150)
    address: str | None = None
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    contact_details: dict[str, str] | None = None
    website: HttpUrl | None = None
    verification_status: str | None = Field(default=None, min_length=1, max_length=30)


class OrganizationResponse(OrganizationFields):
    """Public organization response."""

    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    created_at: datetime
    updated_at: datetime