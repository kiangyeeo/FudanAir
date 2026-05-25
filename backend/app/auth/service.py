from __future__ import annotations

import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import AdminLoginRequest, LoginRequest, RegisterRequest
from app.core.database import transaction
from app.core.exceptions import (
    AuthenticationError,
    InvalidPhoneFormatError,
    PhoneAlreadyExistsError,
    UnauthorizedError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.domains.admin.models import Admin
from app.domains.user.models import User


PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: RegisterRequest) -> User:
        self._validate_phone(payload.phone)
        try:
            with transaction(self.db):
                if self._get_user_by_phone(payload.phone):
                    raise PhoneAlreadyExistsError()
                user = User(
                    phone=payload.phone,
                    name=payload.name,
                    user_password=hash_password(payload.password),
                )
                self.db.add(user)
                self.db.flush()
                self.db.refresh(user)
                return user
        except IntegrityError as exc:
            raise PhoneAlreadyExistsError() from exc

    def login(self, payload: LoginRequest) -> User:
        self._validate_phone(payload.phone)
        user = self._get_user_by_phone(payload.phone)
        if not user:
            raise AuthenticationError("用户暂未注册")
        if not verify_password(payload.password, user.user_password):
            raise AuthenticationError("密码错误，请重试")
        return user

    def admin_login(self, payload: AdminLoginRequest) -> Admin:
        admin = self.db.get(Admin, payload.admin_id)
        if not admin or not verify_password(payload.password, admin.admin_password):
            raise AuthenticationError("管理员账号或密码错误")
        return admin

    def authenticate_user(self, payload: LoginRequest) -> User:
        return self.login(payload)

    def authenticate_admin(self, payload: AdminLoginRequest) -> Admin:
        return self.admin_login(payload)

    def create_token(self, subject: str | int, role: str) -> str:
        return create_access_token(subject=subject, role=role)

    def get_identity(self, subject: str, role: str) -> User | Admin:
        if role == "user":
            return self._get_current_user(subject)
        if role == "admin":
            admin = self.db.get(Admin, subject)
            if admin:
                return admin
        raise UnauthorizedError("未登录或登录已失效")

    def _get_current_user(self, subject: str) -> User:
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise UnauthorizedError("登录凭证无效") from exc
        user = self.db.get(User, user_id)
        if not user:
            raise UnauthorizedError("未登录或登录已失效")
        return user

    def _get_user_by_phone(self, phone: str) -> User | None:
        return self.db.query(User).filter(User.phone == phone).one_or_none()

    @staticmethod
    def _validate_phone(phone: str) -> None:
        if not PHONE_PATTERN.fullmatch(phone):
            raise InvalidPhoneFormatError()
