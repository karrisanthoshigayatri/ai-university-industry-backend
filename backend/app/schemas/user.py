"""User API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


UserRole = Literal[
    "Citizen",
    "Government Officer",
    "HEI Administrator",
    "Faculty / Expert",
    "Student",
    "Industry / MSME / Startup",
    "Research Institution",
    "CSR Organization",
    "System Administrator",
]


class UserCreate(BaseModel):
    """Payload for creating a user."""

    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    role: UserRole
    status: Literal["active", "inactive"] = "active"


class UserUpdate(BaseModel):
    """Payload for partially updating a user."""

    organization_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    role: UserRole | None = None
    status: Literal["active", "inactive"] | None = None


class UserResponse(BaseModel):
    """Public user response without authentication fields."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    organization_id: UUID
    name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    status: Literal["active", "inactive"]
    created_at: datetime
    updated_at: datetime