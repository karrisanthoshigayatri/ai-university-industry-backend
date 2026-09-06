"""HEI Matching API routes — Step 14."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.matching import HeiMatchResponse
from app.services.matching import DEFAULT_TOP_N, run_hei_matching

router = APIRouter(tags=["matching"])

DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]

_ALLOWED_ROLES = {
    "Government Officer",
    "System Administrator",
    "HEI Administrator",
    "Citizen",
    "Government Officer",
}


@router.post(
    "/api/matching/problems/{problem_id}/heis",
    response_model=HeiMatchResponse,
    summary="Match HEIs to a problem (explainable scoring)",
    description=(
        "Runs the deterministic HEI matching engine against a problem's "
        "requirement profile. Results are ranked by match score and persisted "
        "to hei_match. Returns full explanation including matched capabilities, "
        "unmet requirements, resource matches, and score breakdown.\n\n"
        "**Weights:** Capability 40% | Domain 20% | Resource 15% | "
        "Location 10% | Capacity 10% | Other 5%"
    ),
)
def match_heis_to_problem(
    problem_id: UUID,
    db: DB,
    current_user: CU,
    top_n: int = Query(default=DEFAULT_TOP_N, ge=1, le=50, description="Max HEI results to return"),
) -> HeiMatchResponse:
    """Generate and return ranked HEI matches for the given problem."""
    return run_hei_matching(db, problem_id, current_user, top_n=top_n)
