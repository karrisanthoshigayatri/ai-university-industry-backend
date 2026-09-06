"""Problem and ProblemEvidence API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.problem import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    ProblemCreate,
    ProblemResponse,
    ProblemUpdate,
)
from app.services.problem import (
    create_evidence,
    create_problem,
    delete_evidence,
    delete_problem,
    get_evidence,
    get_evidence_list,
    get_problem,
    get_problems,
    update_evidence,
    update_problem,
)


router = APIRouter(prefix="/api/problems", tags=["problems"])


# ── Problem endpoints ──────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProblemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new problem",
)
def create(
    payload: ProblemCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProblemResponse:
    """Create a new problem owned by the authenticated user.

    - `submitter_id` is taken from the JWT — the client cannot set it.
    - `current_status` is always set to **Submitted** by the backend.
    """
    return create_problem(db, payload, current_user)


@router.get(
    "",
    response_model=list[ProblemResponse],
    summary="List problems",
)
def list_problems(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProblemResponse]:
    """Return problems visible to the authenticated user.

    - Citizens see only their own problems.
    - Government Officers and System Administrators see all problems.
    """
    return get_problems(db, current_user)


@router.get(
    "/{problem_id}",
    response_model=ProblemResponse,
    summary="Get a problem by ID",
)
def get_one(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProblemResponse:
    """Return a single problem. Returns 403 if the user has no access."""
    return get_problem(db, problem_id, current_user)


@router.put(
    "/{problem_id}",
    response_model=ProblemResponse,
    summary="Update a problem",
)
def update(
    problem_id: UUID,
    payload: ProblemUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProblemResponse:
    """Update a problem. Only the submitter can update, and only while status is Submitted."""
    return update_problem(db, problem_id, payload, current_user)


@router.delete(
    "/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a problem",
)
def delete(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete a problem. Only the submitter can delete, and only while status is Submitted."""
    delete_problem(db, problem_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Evidence endpoints ─────────────────────────────────────────────────────────

@router.post(
    "/{problem_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add evidence to a problem",
)
def add_evidence(
    problem_id: UUID,
    payload: EvidenceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceResponse:
    """Add evidence to a problem.

    - Only the problem submitter may add evidence.
    - Only allowed while problem status is **Submitted**.
    - `submitted_by` is set from the JWT.
    - `verification_status` is always set to **Pending** by the backend.
    """
    return create_evidence(db, problem_id, payload, current_user)


@router.get(
    "/{problem_id}/evidence",
    response_model=list[EvidenceResponse],
    summary="List all evidence for a problem",
)
def list_evidence(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[EvidenceResponse]:
    """Return all evidence records for the specified problem."""
    return get_evidence_list(db, problem_id, current_user)


@router.get(
    "/{problem_id}/evidence/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Get one evidence record",
)
def get_one_evidence(
    problem_id: UUID,
    evidence_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceResponse:
    """Return a single evidence record by ID."""
    return get_evidence(db, problem_id, evidence_id, current_user)


@router.put(
    "/{problem_id}/evidence/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Update an evidence record",
)
def update_one_evidence(
    problem_id: UUID,
    evidence_id: UUID,
    payload: EvidenceUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceResponse:
    """Update evidence. Only the evidence submitter can update, and only while status is Pending."""
    return update_evidence(db, problem_id, evidence_id, payload, current_user)


@router.delete(
    "/{problem_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an evidence record",
)
def delete_one_evidence(
    problem_id: UUID,
    evidence_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete evidence. Only the evidence submitter can delete, and only while status is Pending."""
    delete_evidence(db, problem_id, evidence_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
