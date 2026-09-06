"""Government validation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.validation import ValidationCreate, ValidationResponse
from app.services.validation import (
    create_validation,
    get_latest_validation,
    get_validation_history,
)


router = APIRouter(prefix="/api/problems", tags=["validation"])


@router.post(
    "/{problem_id}/validation",
    response_model=ValidationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a government validation decision",
)
def validate_problem(
    problem_id: UUID,
    payload: ValidationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ValidationResponse:
    """Record a government officer's validation decision for a problem.

    **Authorization:** Government Officer or System Administrator only.

    **Status transitions:**
    | validation_status          | problem status set to       |
    |----------------------------|-----------------------------|
    | Valid Problem              | Validated                   |
    | Invalid Problem            | Rejected                    |
    | Redirect                   | Redirected                  |
    | More Information Required  | Pending Validation          |

    **Rules:**
    - `validator_id` is taken from the JWT — the client cannot set it.
    - `validated_at` is generated server-side.
    - `rejection_reason` is required when status is *Invalid Problem*.
    - `redirect_destination` is required when status is *Redirect*.
    - Each call creates a new record (full history is preserved).
    """
    return create_validation(db, problem_id, payload, current_user)


@router.get(
    "/{problem_id}/validations",
    response_model=list[ValidationResponse],
    summary="Get full validation history for a problem",
)
def validation_history(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ValidationResponse]:
    """Return all validation records for a problem, oldest first.

    **Authorization:** Government Officers, System Administrators,
    and the original problem submitter.
    """
    return get_validation_history(db, problem_id, current_user)


@router.get(
    "/{problem_id}/validation",
    response_model=ValidationResponse,
    summary="Get the latest validation decision for a problem",
)
def latest_validation(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ValidationResponse:
    """Return only the most recent validation record.

    Returns 404 if the problem has not been validated yet.
    """
    return get_latest_validation(db, problem_id, current_user)
