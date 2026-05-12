from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.service import PHONE_PATTERN
from app.core.database import transaction
from app.core.exceptions import (
    AppException,
    InvalidPhoneFormatError,
    OldPasswordMismatchError,
    PhoneAlreadyExistsError,
    ResourceNotFoundError,
)
from app.core.security import hash_password, verify_password
from app.domains.user.models import User
from app.domains.user.repository import UserRepository
from app.domains.user.schemas import PasswordUpdate, UserProfileUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def get_profile(self, user_id: int) -> User:
        return self._get_user(user_id)

    def update_profile(self, user_id: int, payload: UserProfileUpdate) -> User:
        name = payload.name.strip() if payload.name is not None else None
        phone = payload.phone.strip() if payload.phone is not None else None
        if phone is not None and not PHONE_PATTERN.fullmatch(phone):
            raise InvalidPhoneFormatError()
        try:
            with transaction(self.db):
                user = self._get_user(user_id)
                if phone is not None and phone != user.phone:
                    existing = self.repo.get_by_phone(phone)
                    if existing:
                        raise PhoneAlreadyExistsError()
                return self.repo.update_profile(user, name, phone)
        except IntegrityError as exc:
            raise PhoneAlreadyExistsError() from exc

    def update_password(self, user_id: int, payload: PasswordUpdate) -> None:
        try:
            with transaction(self.db):
                user = self._get_user(user_id)
                if not verify_password(payload.old_password, user.user_password):
                    raise OldPasswordMismatchError()
                self.repo.update_password(user, hash_password(payload.new_password))
        except IntegrityError as exc:
            raise AppException("密码更新失败") from exc

    def _get_user(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if not user:
            raise ResourceNotFoundError(f"用户 {user_id} 不存在")
        return user
