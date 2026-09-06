"""Organization service operations."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


def _get_or_404(db: Session, organization_id: UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return organization


def create_organization(db: Session, payload: OrganizationCreate) -> Organization:
    if payload.official_identifier is not None:
        existing = db.scalar(
            select(Organization).where(
                Organization.official_identifier == payload.official_identifier
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Official identifier already exists",
            )

    organization = Organization(**payload.model_dump())
    if organization.website is not None:
        organization.website = str(organization.website)
    db.add(organization)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization could not be created because a unique value already exists",
        ) from exc
    db.refresh(organization)
    return organization


def get_organization(db: Session, organization_id: UUID) -> Organization:
    return _get_or_404(db, organization_id)


def get_organizations(db: Session, skip: int = 0, limit: int = 100) -> list[Organization]:
    statement = select(Organization).order_by(Organization.name).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_organization(
    db: Session, organization_id: UUID, payload: OrganizationUpdate
) -> Organization:
    organization = _get_or_404(db, organization_id)
    updates = payload.model_dump(exclude_unset=True)
    if "official_identifier" in updates and updates["official_identifier"] is not None:
        existing = db.scalar(
            select(Organization).where(
                Organization.official_identifier == updates["official_identifier"],
                Organization.organization_id != organization_id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Official identifier already exists",
            )
    if "website" in updates and updates["website"] is not None:
        updates["website"] = str(updates["website"])
    for field, value in updates.items():
        setattr(organization, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization could not be updated because a unique value already exists",
        ) from exc
    db.refresh(organization)
    return organization


def delete_organization(db: Session, organization_id: UUID) -> None:
    organization = _get_or_404(db, organization_id)
    db.delete(organization)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization cannot be deleted while it has related records",
        ) from exc