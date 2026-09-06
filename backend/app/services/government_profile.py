"""Government profile service operations."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.government_profile import GovernmentProfile
from app.models.organization import Organization
from app.schemas.government_profile import GovernmentProfileCreate, GovernmentProfileUpdate


ALLOWED_ORGANIZATION_TYPES = {"Government", "PRI", "ULB"}


def _get_or_404(db: Session, government_id: UUID) -> GovernmentProfile:
    profile = db.get(GovernmentProfile, government_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Government profile not found",
        )
    return profile


def _get_organization_or_404(db: Session, organization_id: UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    if organization.organization_type not in ALLOWED_ORGANIZATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Government profiles are allowed only for Government, PRI, or ULB organizations",
        )
    return organization


def _ensure_unique_organization(db: Session, organization_id: UUID, government_id: UUID | None = None) -> None:
    statement = select(GovernmentProfile).where(
        GovernmentProfile.organization_id == organization_id
    )
    if government_id is not None:
        statement = statement.where(GovernmentProfile.government_id != government_id)
    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already has a government profile",
        )


def create_government_profile(db: Session, payload: GovernmentProfileCreate) -> GovernmentProfile:
    _get_organization_or_404(db, payload.organization_id)
    _ensure_unique_organization(db, payload.organization_id)
    profile = GovernmentProfile(**payload.model_dump())
    db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already has a government profile",
        ) from exc
    db.refresh(profile)
    return profile


def get_government_profile(db: Session, government_id: UUID) -> GovernmentProfile:
    return _get_or_404(db, government_id)


def get_government_profiles(db: Session, skip: int = 0, limit: int = 100) -> list[GovernmentProfile]:
    statement = (
        select(GovernmentProfile)
        .order_by(GovernmentProfile.department_name)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def update_government_profile(
    db: Session, government_id: UUID, payload: GovernmentProfileUpdate
) -> GovernmentProfile:
    profile = _get_or_404(db, government_id)
    updates = payload.model_dump(exclude_unset=True)
    if "organization_id" in updates and updates["organization_id"] is not None:
        _get_organization_or_404(db, updates["organization_id"])
        _ensure_unique_organization(db, updates["organization_id"], government_id)
    for field, value in updates.items():
        setattr(profile, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already has a government profile",
        ) from exc
    db.refresh(profile)
    return profile


def delete_government_profile(db: Session, government_id: UUID) -> None:
    profile = _get_or_404(db, government_id)
    db.delete(profile)
    db.commit()