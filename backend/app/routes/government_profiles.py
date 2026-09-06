"""Government profile API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.government_profile import (
    GovernmentProfileCreate,
    GovernmentProfileResponse,
    GovernmentProfileUpdate,
)
from app.services.government_profile import (
    create_government_profile,
    delete_government_profile,
    get_government_profile,
    get_government_profiles,
    update_government_profile,
)


router = APIRouter(prefix="/api/government-profiles", tags=["government-profiles"])


@router.post("", response_model=GovernmentProfileResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: GovernmentProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Government Officer", "System Administrator")),
) -> GovernmentProfileResponse:
    return create_government_profile(db, payload)


@router.get("", response_model=list[GovernmentProfileResponse])
def list_all(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[GovernmentProfileResponse]:
    return get_government_profiles(db, skip, min(limit, 100))


@router.get("/{government_id}", response_model=GovernmentProfileResponse)
def get_one(government_id: UUID, db: Session = Depends(get_db)) -> GovernmentProfileResponse:
    return get_government_profile(db, government_id)


@router.put("/{government_id}", response_model=GovernmentProfileResponse)
def update(
    government_id: UUID,
    payload: GovernmentProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Government Officer", "System Administrator")),
) -> GovernmentProfileResponse:
    return update_government_profile(db, government_id, payload)


@router.delete("/{government_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    government_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Government Officer", "System Administrator")),
) -> Response:
    delete_government_profile(db, government_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)