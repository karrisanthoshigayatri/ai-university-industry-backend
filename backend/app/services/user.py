"""User service operations."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def _get_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _ensure_organization_exists(db: Session, organization_id: UUID) -> None:
    if db.get(Organization, organization_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization reference is invalid",
        )


def _ensure_email_is_available(
    db: Session, email: str, user_id: UUID | None = None
) -> None:
    statement = select(User).where(User.email == email)
    if user_id is not None:
        statement = statement.where(User.user_id != user_id)
    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )


def create_user(db: Session, payload: UserCreate) -> User:
    _ensure_organization_exists(db, payload.organization_id)
    _ensure_email_is_available(db, str(payload.email))
    user = User(**payload.model_dump())
    user.email = str(user.email)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be created because a unique value already exists",
        ) from exc
    db.refresh(user)
    return user


def get_user(db: Session, user_id: UUID) -> User:
    return _get_or_404(db, user_id)


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    statement = select(User).order_by(User.name).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_user(db: Session, user_id: UUID, payload: UserUpdate) -> User:
    user = _get_or_404(db, user_id)
    updates = payload.model_dump(exclude_unset=True)
    if "organization_id" in updates and updates["organization_id"] is not None:
        _ensure_organization_exists(db, updates["organization_id"])
    if "email" in updates and updates["email"] is not None:
        updates["email"] = str(updates["email"])
        _ensure_email_is_available(db, updates["email"], user_id)
    for field, value in updates.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be updated because a unique value already exists",
        ) from exc
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: UUID) -> None:
    user = _get_or_404(db, user_id)
    db.delete(user)
    db.commit()