from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.deps import get_db
from app.domains.user.schemas import (
    PasswordUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.domains.user.service import UserService


router = APIRouter(prefix="/users", tags=["user"])


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    return UserService(db).get_profile(user_id)


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    payload: UserProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    return UserService(db).update_profile(user_id, payload)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def update_my_password(
    payload: PasswordUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    UserService(db).update_password(user_id, payload)
