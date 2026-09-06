"""Authentication request and response schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRole


class RegisterRequest(BaseModel):
    """Public registration payload."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    organization_id: UUID
    role: UserRole


class LoginRequest(BaseModel):
    """Email and password login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """JWT response."""

    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    """Safe authenticated-user response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    organization_id: UUID
    name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    status: str