"""Authentication service operations."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


def register_user(db: Session, payload: RegisterRequest) -> User:
    if payload.role == "System Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator accounts cannot be self-registered",
        )
    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization reference is invalid",
        )
    if db.scalar(select(User).where(User.email == str(payload.email))) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    user = User(
        organization_id=payload.organization_id,
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        role=payload.role,
        password_hash=hash_password(payload.password),
        status="active",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> str:
    user = db.scalar(select(User).where(User.email == str(payload.email)))
    if user is None or user.password_hash is None:
        raise INVALID_CREDENTIALS
    if user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise INVALID_CREDENTIALS
    return create_access_token(str(user.user_id), user.role)