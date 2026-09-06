"""Pydantic schemas for HEI matching responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Per-capability detail inside a match result ────────────────────────────────

class CapabilityMatchDetail(BaseModel):
    capability_id: str
    capability_name: str
    required_level: float | None = None
    available_level: float | None = None
    match_status: str          # "matched" | "partial" | "unmet"
    source: str                # "hei" | "faculty" | "resource"


# ── Per-resource detail ────────────────────────────────────────────────────────

class ResourceMatchDetail(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    matched: bool


# ── Hard-constraint result ─────────────────────────────────────────────────────

class ConstraintResult(BaseModel):
    constraint_name: str
    passed: bool
    reason: str


# ── Score breakdown (explainability) ──────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    capability_score: float = Field(description="0–40 pts — capability/skill match (40%)")
    domain_score: float     = Field(description="0–20 pts — domain match (20%)")
    resource_score: float   = Field(description="0–15 pts — resource match (15%)")
    location_score: float   = Field(description="0–10 pts — location match (10%)")
    capacity_score: float   = Field(description="0–10 pts — capacity/availability (10%)")
    other_score: float      = Field(description="0–5 pts  — eligibility/budget (5%)")
    total: float            = Field(description="0–100 total match score")


# ── Single HEI match result ────────────────────────────────────────────────────

class HeiMatchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: UUID
    hei_id: UUID
    hei_name: str
    match_score: float
    rank: int
    score_breakdown: ScoreBreakdown
    matched_capabilities: list[CapabilityMatchDetail]
    unmet_requirements: list[CapabilityMatchDetail]
    matched_resources: list[ResourceMatchDetail]
    constraint_results: list[ConstraintResult]
    match_reasons: list[str]
    model_version: str
    constraints_passed: bool


# ── Top-level response from the matching endpoint ─────────────────────────────

class HeiMatchResponse(BaseModel):
    problem_id: UUID
    problem_title: str
    total_matches: int
    matches: list[HeiMatchResult]
    model_version: str
    generated_at: datetime
