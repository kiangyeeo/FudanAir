from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_identity
from app.auth.schemas import (
    AdminLoginRequest,
    AdminSession,
    LoginRequest,
    RegisterRequest,
    UserRegisterResponse,
    UserSession,
)
from app.auth.service import AuthService
from app.config import settings
from app.core.logging import get_logger
from app.deps import get_db
from app.domains.admin.models import Admin
from app.domains.user.models import User


COOKIE_NAME = "access_token"
COOKIE_MAX_AGE_SECONDS = settings.JWT_EXPIRE_MINUTES * 60

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=UserRegisterResponse)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserRegisterResponse:
    user = AuthService(db).register(payload)
    return UserRegisterResponse(
        user_id=user.user_id,
        phone=user.phone,
        name=user.name,
    )


@router.post("/login", response_model=UserSession)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserSession:
    service = AuthService(db)
    user = service.login(payload)
    _set_auth_cookie(response, service.create_token(user.user_id, "user"))
    logger.info("用户登录成功 user_id=%s", user.user_id)
    return _user_session(user)


@router.post("/admin-login", response_model=AdminSession)
def admin_login(
    payload: AdminLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AdminSession:
    service = AuthService(db)
    admin = service.admin_login(payload)
    _set_auth_cookie(response, service.create_token(admin.admin_id, "admin"))
    logger.info("管理员登录成功 admin_id=%s", admin.admin_id)
    return _admin_session(admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    _identity: User | Admin = Depends(get_current_identity),
) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/", samesite="lax")
    return None


@router.get("/me", response_model=UserSession | AdminSession)
def me(identity: User | Admin = Depends(get_current_identity)) -> UserSession | AdminSession:
    if isinstance(identity, User):
        return _user_session(identity)
    return _admin_session(identity)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _user_session(user: User) -> UserSession:
    return UserSession(
        user_id=user.user_id,
        phone=user.phone,
        name=user.name,
    )


def _admin_session(admin: Admin) -> AdminSession:
    return AdminSession(
        admin_id=admin.admin_id,
        name=admin.admin_name,
    )
