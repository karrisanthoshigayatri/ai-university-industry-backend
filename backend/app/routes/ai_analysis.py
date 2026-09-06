"""AI Problem Analysis API route."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.ai_analysis import run_ai_analysis


router = APIRouter(tags=["ai-analysis"])


@router.post(
    "/api/problems/{problem_id}/ai-analysis",
    summary="Run Qwen2.5 AI analysis on a validated problem",
)
def ai_analysis(
    problem_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Run Qwen2.5 AI analysis on a government-validated problem.

    **Pre-conditions:**
    - Problem must exist and be accessible to the caller.
    - Problem must have `current_status = Validated`.
      If not validated, returns **422** with a clear message.

    **What the AI produces:**
    - **Categories** — domain classification mapped to canonical capabilities.
    - **Priority** — severity, urgency, and strategic relevance scores.
    - **Requirements** — high-level support/resource requirements.
    - **Capabilities** — granular capability requirements for matching.

    **AI does NOT:**
    - Change the problem status.
    - Replace government validation.
    - Auto-match universities or industry partners.

    **Unmapped capabilities** (not found in the Capability table) are returned
    with `capability_id = null` and `mapped = false` for human review.

    Each call creates new records — history is preserved.
    """
    return run_ai_analysis(db, problem_id, current_user)
