"""Problem and ProblemEvidence Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Literal types ──────────────────────────────────────────────────────────────

SourceType = Literal[
    "Citizen",
    "Community",
    "PRI",
    "ULB",
    "Government",
]

ProblemStatus = Literal[
    "Submitted",
    "Similar Found",
    "Pending Validation",
    "Validated",
    "Rejected",
    "Redirected",
    "Linked to Existing Problem",
    "Matched",
    "Accepted",
    "Active",
    "Completed",
]

EvidenceType = Literal[
    "Photograph",
    "Video",
    "Document",
    "Geo-location",
    "Government record",
    "Citizen report",
]

EvidenceVerificationStatus = Literal["Pending", "Verified", "Rejected"]


# ── Problem schemas ────────────────────────────────────────────────────────────

class ProblemCreate(BaseModel):
    """Payload the client sends to create a new problem.

    The client must NOT supply submitter_id, current_status, submission_date,
    created_at or updated_at — the backend fills those in.
    """

    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    source_type: SourceType
    location: str | None = Field(default=None, max_length=500)


class ProblemUpdate(BaseModel):
    """Fields the submitter may change while the problem is still 'Submitted'."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, min_length=1)
    source_type: SourceType | None = None
    location: str | None = Field(default=None, max_length=500)


class ProblemResponse(BaseModel):
    """Full problem record returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    problem_id: UUID
    title: str
    description: str
    submitter_id: UUID
    source_type: SourceType
    location: str | None
    submission_date: datetime
    current_status: ProblemStatus
    created_at: datetime
    updated_at: datetime


# ── Evidence schemas ───────────────────────────────────────────────────────────

class EvidenceCreate(BaseModel):
    """Payload for adding evidence to a problem.

    The client must NOT supply submitted_by, verification_status or created_at.
    """

    evidence_type: EvidenceType
    file_reference: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    captured_at: datetime | None = None


class EvidenceUpdate(BaseModel):
    """Fields the evidence submitter may change while status is 'Pending'."""

    evidence_type: EvidenceType | None = None
    file_reference: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    captured_at: datetime | None = None


class EvidenceResponse(BaseModel):
    """Full evidence record returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: UUID
    problem_id: UUID
    evidence_type: EvidenceType
    file_reference: str | None
    description: str | None
    latitude: float | None
    longitude: float | None
    captured_at: datetime | None
    submitted_by: UUID
    verification_status: EvidenceVerificationStatus
    created_at: datetime
