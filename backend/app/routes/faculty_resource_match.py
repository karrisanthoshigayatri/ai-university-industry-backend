"""Faculty / Resource contextual matching routes — Step 15."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.faculty_resource_match import FacultyResourceMatchResponse
from app.services.faculty_resource_match import DEFAULT_TOP_N, run_fr_matching

router = APIRouter(tags=["matching"])

DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


@router.post(
    "/api/matching/problems/{problem_id}/faculty-resources",
    response_model=FacultyResourceMatchResponse,
    summary="Match faculty and resources to a validated problem",
    description=(
        "Runs the deterministic faculty/resource matching engine. "
        "Problem must be in Validated, Matched, Accepted, or Active status.\n\n"
        "**Weights:** Capability 50% | Domain 20% | Evidence 10% | "
        "Availability 10% | Constraints 10%"
    ),
)
def match_faculty_resources(
    problem_id: UUID,
    db: DB,
    current_user: CU,
    hei_id: UUID | None = Query(default=None, description="Limit to a specific HEI"),
    top_n: int = Query(default=DEFAULT_TOP_N, ge=1, le=100,
                       description="Maximum results to return"),
) -> FacultyResourceMatchResponse:
    """Find the most suitable faculty experts and institutional resources for a problem."""
    return run_fr_matching(db, problem_id, current_user, hei_id=hei_id, top_n=top_n)
