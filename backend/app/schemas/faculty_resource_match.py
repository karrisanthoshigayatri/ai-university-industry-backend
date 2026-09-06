"""Pydantic schemas for Faculty / Resource contextual matching."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MatchType = Literal["Faculty", "Resource"]


class FRCapabilityDetail(BaseModel):
    capability_id: str
    capability_name: str
    required_level: float | None = None
    available_level: float | None = None
    match_status: str   # "matched" | "partial" | "unmet"


class FRConstraintResult(BaseModel):
    constraint_name: str
    passed: bool
    reason: str


class FRScoreBreakdown(BaseModel):
    capability_score: float = Field(description="0–50 pts (50%)")
    domain_score: float     = Field(description="0–20 pts (20%)")
    evidence_score: float   = Field(description="0–10 pts (10%)")
    availability_score: float = Field(description="0–10 pts (10%)")
    constraint_score: float = Field(description="0–10 pts (10%)")
    total: float


class FacultyResourceMatchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: UUID
    hei_id: UUID
    match_type: MatchType
    faculty_id: UUID | None
    faculty_name: str | None
    faculty_designation: str | None
    resource_id: UUID | None
    resource_name: str | None
    resource_type: str | None
    rank: int
    match_score: float
    score_breakdown: FRScoreBreakdown
    matched_capabilities: list[FRCapabilityDetail]
    unmet_requirements: list[FRCapabilityDetail]
    constraint_results: list[FRConstraintResult]
    match_reasons: list[str]
    model_version: str
    constraints_passed: bool


class FacultyResourceMatchResponse(BaseModel):
    problem_id: UUID
    problem_title: str
    hei_id: UUID | None
    total_matches: int
    faculty_matches: int
    resource_matches: int
    matches: list[FacultyResourceMatchResult]
    model_version: str
    generated_at: datetime
