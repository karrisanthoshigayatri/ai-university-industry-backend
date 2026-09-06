"""User API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import create_user, delete_user, get_user, get_users, update_user


router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    return create_user(db, payload)


@router.get("", response_model=list[UserResponse])
def list_all(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[UserResponse]:
    return get_users(db, skip, min(limit, 100))


@router.get("/{user_id}", response_model=UserResponse)
def get_one(user_id: UUID, db: Session = Depends(get_db)) -> UserResponse:
    return get_user(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update(
    user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db)
) -> UserResponse:
    return update_user(db, user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(user_id: UUID, db: Session = Depends(get_db)) -> Response:
    delete_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)