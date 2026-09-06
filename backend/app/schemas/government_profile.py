"""Government profile API schemas."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


NonEmptyText = Annotated[str, Field(min_length=1)]


class GovernmentProfileFields(BaseModel):
    """Shared government profile input fields."""

    organization_id: UUID
    department_name: NonEmptyText = Field(max_length=255)
    administrative_level: NonEmptyText = Field(max_length=50)
    jurisdiction: NonEmptyText = Field(max_length=255)
    nodal_officer: NonEmptyText = Field(max_length=255)
    designation: NonEmptyText = Field(max_length=150)
    contact_details: dict[str, str] | None = None


class GovernmentProfileCreate(GovernmentProfileFields):
    """Payload for creating a government profile."""


class GovernmentProfileUpdate(BaseModel):
    """Payload for partially updating a government profile."""

    organization_id: UUID | None = None
    department_name: NonEmptyText | None = Field(default=None, max_length=255)
    administrative_level: NonEmptyText | None = Field(default=None, max_length=50)
    jurisdiction: NonEmptyText | None = Field(default=None, max_length=255)
    nodal_officer: NonEmptyText | None = Field(default=None, max_length=255)
    designation: NonEmptyText | None = Field(default=None, max_length=150)
    contact_details: dict[str, str] | None = None


class GovernmentProfileResponse(GovernmentProfileFields):
    """Public government profile response."""

    model_config = ConfigDict(from_attributes=True)

    government_id: UUID
    created_at: datetime
    updated_at: datetime