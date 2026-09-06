"""Similarity check and relation decision API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.similarity import (
    RelationDecisionRequest,
    RelationResponse,
    SimilarityCheckResponse,
)
from app.services.similarity import decide_relation, run_similarity_check


router = APIRouter(tags=["similarity"])


@router.post(
    "/api/problems/{problem_id}/similarity-check",
    response_model=SimilarityCheckResponse,
    summary="Run AI similarity check for a problem",
)
def similarity_check(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SimilarityCheckResponse:
    """Compare this problem against existing problems using embeddings.

    - Returns the top-K candidates above the configured similarity threshold.
    - Persists **Similar** PROBLEM_RELATION records for new matches.
    - **Never** automatically marks any problem as Duplicate.
    - Updates the source problem status to **Similar Found** if matches exist.

    Authorization: any authenticated user who can view the problem.
    """
    return run_similarity_check(db, problem_id, current_user)


@router.put(
    "/api/problems/relations/{relation_id}/decision",
    response_model=RelationResponse,
    summary="Record a human decision on a problem relation",
)
def relation_decision(
    relation_id: UUID,
    payload: RelationDecisionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RelationResponse:
    """Confirm or reject an AI-generated similarity recommendation.

    - Any authenticated user may confirm **Similar** or **Related**.
    - Only **Government Officers** and **System Administrators** may confirm
      **Duplicate**, **Consolidated**, or **Linked** relationships.
    - Confirming Duplicate/Linked/Consolidated updates the source problem
      status to **Linked to Existing Problem**.
    - Stores `decided_by` (from JWT) and `decided_at` (server time).
    """
    return decide_relation(db, relation_id, payload, current_user)
