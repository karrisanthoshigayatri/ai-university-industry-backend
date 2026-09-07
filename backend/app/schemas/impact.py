"""Pydantic schemas for ImpactRecord, Beneficiary, Feedback, Notification and AuditLog."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Impact Record ──────────────────────────────────────────────────────────────

class ImpactCreate(BaseModel):
    metric: str = Field(min_length=1)
    baseline_value: float | None = None
    target_value: float | None = None
    achieved_value: float | None = None
    unit: str | None = None
    location: dict | None = None
    evidence: str | None = None
    measured_at: datetime | None = None


class ImpactUpdate(BaseModel):
    metric: str | None = Field(default=None, min_length=1)
    baseline_value: float | None = None
    target_value: float | None = None
    achieved_value: float | None = None
    unit: str | None = None
    location: dict | None = None
    evidence: str | None = None
    measured_at: datetime | None = None


class ImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    impact_id: UUID
    project_id: UUID
    metric: str
    baseline_value: float | None
    target_value: float | None
    achieved_value: float | None
    unit: str | None
    location: dict | None
    evidence: str | None
    measured_at: datetime | None
    verified_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ImpactSummary(BaseModel):
    project_id: UUID
    total_records: int
    metrics: list[dict]  # {metric, achieved_pct}


# ── Beneficiary ────────────────────────────────────────────────────────────────

class BeneficiaryCreate(BaseModel):
    beneficiary_type: str = Field(min_length=1)
    location: dict | None = None
    estimated_count: int | None = Field(default=None, ge=0)
    affected_domain: str | None = None


class BeneficiaryUpdate(BaseModel):
    beneficiary_type: str | None = Field(default=None, min_length=1)
    location: dict | None = None
    estimated_count: int | None = Field(default=None, ge=0)
    affected_domain: str | None = None


class BeneficiaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    beneficiary_id: UUID
    project_id: UUID
    beneficiary_type: str
    location: dict | None
    estimated_count: int | None
    affected_domain: str | None
    created_at: datetime
    updated_at: datetime


class BeneficiarySummary(BaseModel):
    project_id: UUID
    total_beneficiaries: int
    breakdown: list[dict]


# ── Feedback ───────────────────────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    project_id: UUID | None = None
    problem_id: UUID | None = None
    feedback_type: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    feedback_id: UUID
    project_id: UUID | None
    problem_id: UUID | None
    submitted_by: UUID | None
    feedback_type: str | None
    rating: int | None
    comment: str | None
    submitted_at: datetime


class FeedbackSummary(BaseModel):
    total: int
    average_rating: float | None
    rating_distribution: dict[str, int]


# ── Notification ───────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notification_id: UUID
    recipient_id: UUID
    event_type: str
    reference_type: str | None
    reference_id: UUID | None
    message: str
    status: str
    created_at: datetime
    read_at: datetime | None


# ── AuditLog ───────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    audit_id: UUID
    actor_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    old_value: dict | None
    new_value: dict | None
    timestamp: datetime
    reason: str | None
