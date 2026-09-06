"""Validation request and response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ValidationStatus = Literal[
    "Valid Problem",
    "Invalid Problem",
    "Redirect",
    "More Information Required",
]


class ValidationCreate(BaseModel):
    """Payload a government officer sends to validate a problem.

    Business rules enforced at the schema level:
    - 'Invalid Problem' requires rejection_reason.
    - 'Redirect' requires redirect_destination.
    The client must NOT supply validator_id or validated_at.
    """

    validation_status: ValidationStatus
    field_verification_required: bool = False
    field_visit_details: str | None = Field(default=None)
    evidence_review: str | None = Field(default=None)
    remarks: str | None = Field(default=None)
    rejection_reason: str | None = Field(default=None, min_length=1)
    redirect_destination: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def check_required_fields(self) -> "ValidationCreate":
        if self.validation_status == "Invalid Problem":
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError(
                    "rejection_reason is required when validation_status is 'Invalid Problem'"
                )
        if self.validation_status == "Redirect":
            if not self.redirect_destination or not self.redirect_destination.strip():
                raise ValueError(
                    "redirect_destination is required when validation_status is 'Redirect'"
                )
        return self


class ValidationResponse(BaseModel):
    """Full validation record returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    validation_id: UUID
    problem_id: UUID
    validator_id: UUID
    validation_status: ValidationStatus
    field_verification_required: bool | None
    field_visit_details: str | None
    evidence_review: str | None
    remarks: str | None
    rejection_reason: str | None
    redirect_destination: str | None
    validated_at: datetime
