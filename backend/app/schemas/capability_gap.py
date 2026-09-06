"""Pydantic schemas for CapabilityGap and PartnerMatch."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Capability Gap ─────────────────────────────────────────────────────────────

class GapDetail(BaseModel):
    capability_id: str
    capability_name: str
    required_level: float
    available_level: float
    gap_level: float
    criticality: float
    status: str
    recommended_support: str | None


class GapAnalysisResponse(BaseModel):
    project_id: UUID
    total_requirements: int
    gaps_found: int
    no_gap_count: int
    gaps: list[GapDetail]
    generated_at: datetime


class CapabilityGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    gap_id: UUID
    project_id: UUID
    capability_id: UUID
    required_level: float | None
    available_level: float | None
    gap_level: float | None
    criticality: float | None
    recommended_support: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CapabilityGapUpdate(BaseModel):
    recommended_support: str | None = None
    status: str | None = None


# ── Partner Match ──────────────────────────────────────────────────────────────

class PartnerCapDetail(BaseModel):
    capability_id: str
    capability_name: str
    required_level: float | None
    partner_level: float | None
    match_status: str


class SupportOfferingDetail(BaseModel):
    offering_id: str
    support_type: str
    title: str | None
    status: str


class PartnerMatchResult(BaseModel):
    match_id: UUID
    partner_id: UUID
    partner_name: str
    partner_type: str
    rank: int
    match_score: float
    score_breakdown: dict
    matched_capabilities: list[PartnerCapDetail]
    unmet_requirements: list[PartnerCapDetail]
    support_matches: list[SupportOfferingDetail]
    constraint_results: list[dict]
    match_reasons: list[str]
    model_version: str
    constraints_passed: bool


class PartnerMatchResponse(BaseModel):
    project_id: UUID
    total_matches: int
    matches: list[PartnerMatchResult]
    model_version: str
    generated_at: datetime
