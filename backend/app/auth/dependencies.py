from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.core.database import SessionLocal
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import decode_access_token
from app.domains.admin.models import Admin
from app.domains.user.models import User


def get_auth_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_identity(
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
    db: Session = Depends(get_auth_db),
) -> User | Admin:
    if not access_token:
        raise UnauthorizedError("You are not signed in or your session has expired.")
    payload = decode_access_token(access_token)
    return AuthService(db).get_identity(payload["sub"], payload["role"])


def get_current_user(
    identity: User | Admin = Depends(get_current_identity),
) -> User:
    if not isinstance(identity, User):
        raise PermissionDeniedError("User access is required.")
    return identity


def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return int(user.user_id)


def get_current_admin(
    identity: User | Admin = Depends(get_current_identity),
) -> Admin:
    if not isinstance(identity, Admin):
        raise PermissionDeniedError("Admin access is required.")
    return identity


def get_current_admin_id(admin: Admin = Depends(get_current_admin)) -> str:
    return str(admin.admin_id)


def require_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    return admin
