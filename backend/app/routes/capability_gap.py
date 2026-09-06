"""Capability Gap and Partner Matching routes — Steps 19–20."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.capability_gap import (
    CapabilityGapResponse, CapabilityGapUpdate,
    GapAnalysisResponse, PartnerMatchResponse,
)
from app.services.capability_gap import (
    analyze_gaps, get_gap, get_partner_matches,
    list_gaps, run_partner_matching, update_gap,
)

router = APIRouter(tags=["capability-gaps", "partner-matching"])
DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Capability Gaps ───────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/capability-gaps/analyze",
             response_model=GapAnalysisResponse, summary="Analyze capability gaps for project")
def analyze_gaps_route(project_id: UUID, db: DB, cu: CU) -> GapAnalysisResponse:
    return analyze_gaps(db, project_id, cu)


@router.get("/api/projects/{project_id}/capability-gaps",
            response_model=list[CapabilityGapResponse], summary="List capability gaps")
def list_gaps_route(project_id: UUID, db: DB, _: CU) -> list[CapabilityGapResponse]:
    return list_gaps(db, project_id)


@router.get("/api/projects/{project_id}/capability-gaps/{gap_id}",
            response_model=CapabilityGapResponse, summary="Get capability gap")
def get_gap_route(project_id: UUID, gap_id: UUID, db: DB, _: CU) -> CapabilityGapResponse:
    return get_gap(db, project_id, gap_id)


@router.put("/api/projects/{project_id}/capability-gaps/{gap_id}",
            response_model=CapabilityGapResponse, summary="Update capability gap")
def update_gap_route(project_id: UUID, gap_id: UUID, payload: CapabilityGapUpdate,
                     db: DB, cu: CU) -> CapabilityGapResponse:
    return update_gap(db, project_id, gap_id, payload, cu)


# ── Partner Matching ───────────────────────────────────────────────────────────

@router.post("/api/matching/projects/{project_id}/partners",
             response_model=PartnerMatchResponse,
             summary="Match partners to project capability gaps")
def match_partners(project_id: UUID, db: DB, cu: CU,
                   top_n: int = Query(default=10, ge=1, le=50)) -> PartnerMatchResponse:
    return run_partner_matching(db, project_id, cu, top_n=top_n)


@router.get("/api/matching/projects/{project_id}/partners",
            response_model=PartnerMatchResponse,
            summary="Get saved partner match results for a project")
def get_partner_matches_route(project_id: UUID, db: DB, cu: CU) -> PartnerMatchResponse:
    return get_partner_matches(db, project_id, cu)
