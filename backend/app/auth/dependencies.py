from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import decode_access_token
from app.deps import get_db
from app.domains.admin.models import Admin
from app.domains.user.models import User


def get_current_identity(
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
    db: Session = Depends(get_db),
) -> User | Admin:
    if not access_token:
        raise UnauthorizedError("未登录或登录已失效")
    payload = decode_access_token(access_token)
    return AuthService(db).get_identity(payload["sub"], payload["role"])


def get_current_user(
    identity: User | Admin = Depends(get_current_identity),
) -> User:
    if not isinstance(identity, User):
        raise PermissionDeniedError("需要用户权限")
    return identity


def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return int(user.user_id)


def get_current_admin(
    identity: User | Admin = Depends(get_current_identity),
) -> Admin:
    if not isinstance(identity, Admin):
        raise PermissionDeniedError("需要管理员权限")
    return identity


def get_current_admin_id(admin: Admin = Depends(get_current_admin)) -> str:
    return str(admin.admin_id)


def require_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    return admin
