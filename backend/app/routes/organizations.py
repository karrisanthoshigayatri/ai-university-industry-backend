"""Organization API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.services.organization import (
    create_organization,
    delete_organization,
    get_organization,
    get_organizations,
    update_organization,
)


router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Government Officer", "System Administrator")),
) -> OrganizationResponse:
    return create_organization(db, payload)


@router.get("", response_model=list[OrganizationResponse])
def list_all(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[OrganizationResponse]:
    return get_organizations(db, skip, min(limit, 100))


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_one(organization_id: UUID, db: Session = Depends(get_db)) -> OrganizationResponse:
    return get_organization(db, organization_id)


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update(
    organization_id: UUID,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Government Officer", "System Administrator")),
) -> OrganizationResponse:
    return update_organization(db, organization_id, payload)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    organization_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("System Administrator")),
) -> Response:
    delete_organization(db, organization_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)