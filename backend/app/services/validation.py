"""Government validation service operations.

Business rules:
- Only Government Officers and System Administrators may create validations.
- validator_id always comes from the authenticated JWT user.
- validated_at is always generated server-side.
- Each validation_status drives a specific PROBLEM.current_status transition.
- Full history is preserved — old records are never deleted or overwritten.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.user import User
from app.models.validation import Validation
from app.schemas.validation import ValidationCreate, ValidationResponse


logger = logging.getLogger(__name__)

# Roles allowed to perform government validation
_VALIDATOR_ROLES = {"Government Officer", "System Administrator"}

# Mapping: validation_status → PROBLEM.current_status
_STATUS_MAP: dict[str, str] = {
    "Valid Problem":            "Validated",
    "Invalid Problem":          "Rejected",
    "Redirect":                 "Redirected",
    "More Information Required": "Pending Validation",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_problem_or_404(db: Session, problem_id: UUID) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found",
        )
    return problem


def _assert_validator_role(current_user: User) -> None:
    if current_user.role not in _VALIDATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Government Officers and System Administrators may validate problems.",
        )


def _assert_can_view(problem: Problem, current_user: User) -> None:
    """Allow submitter and privileged users to view validation history."""
    if current_user.role in _VALIDATOR_ROLES:
        return
    if problem.submitter_id == current_user.user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view validations for this problem.",
    )


def _audit(event: str, actor_id: UUID, detail: str) -> None:
    """Audit hook — replace with full Audit Log service in a later step."""
    logger.info("[AUDIT] event=%s actor=%s detail=%s", event, actor_id, detail)


# ── Create validation ──────────────────────────────────────────────────────────

def create_validation(
    db: Session,
    problem_id: UUID,
    payload: ValidationCreate,
    current_user: User,
) -> Validation:
    """Create a validation record and update the problem status accordingly."""

    _assert_validator_role(current_user)
    problem = _get_problem_or_404(db, problem_id)

    # Build the validation record; validator_id and validated_at come from server
    validation = Validation(
        problem_id=problem_id,
        validator_id=current_user.user_id,
        validation_status=payload.validation_status,
        field_verification_required=payload.field_verification_required,
        field_visit_details=payload.field_visit_details,
        evidence_review=payload.evidence_review,
        remarks=payload.remarks,
        rejection_reason=payload.rejection_reason,
        redirect_destination=payload.redirect_destination,
        validated_at=datetime.now(timezone.utc),
    )
    db.add(validation)

    # Drive problem status transition
    new_problem_status = _STATUS_MAP[payload.validation_status]
    problem.current_status = new_problem_status

    db.commit()
    db.refresh(validation)

    _audit(
        "GOVERNMENT_VALIDATION",
        current_user.user_id,
        (
            f"problem={problem_id} "
            f"validation_status={payload.validation_status} "
            f"problem_status_now={new_problem_status}"
        ),
    )

    return validation


# ── Read validations ───────────────────────────────────────────────────────────

def get_validation_history(
    db: Session,
    problem_id: UUID,
    current_user: User,
) -> list[Validation]:
    """Return all validation records for a problem (oldest first)."""
    problem = _get_problem_or_404(db, problem_id)
    _assert_can_view(problem, current_user)

    stmt = (
        select(Validation)
        .where(Validation.problem_id == problem_id)
        .order_by(Validation.validated_at.asc())
    )
    return list(db.scalars(stmt).all())


def get_latest_validation(
    db: Session,
    problem_id: UUID,
    current_user: User,
) -> Validation:
    """Return the most recent validation record for a problem."""
    problem = _get_problem_or_404(db, problem_id)
    _assert_can_view(problem, current_user)

    stmt = (
        select(Validation)
        .where(Validation.problem_id == problem_id)
        .order_by(Validation.validated_at.desc())
        .limit(1)
    )
    validation = db.scalar(stmt)
    if validation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validation records found for this problem.",
        )
    return validation
