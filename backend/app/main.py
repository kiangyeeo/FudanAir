from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.auth.schemas import REGISTER_PASSWORD_MIN_LENGTH
from app.auth.service import PHONE_PATTERN
from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.domains.airline.router import (
    aircraft_type_router,
    airline_router,
)
from app.domains.admin.router import router as admin_router
from app.domains.city.router import airport_router, city_router
from app.domains.flight.router import flight_instance_router, flight_router
from app.domains.order.router import admin_order_router, order_router
from app.domains.passenger.router import router as passenger_router
from app.domains.user.router import router as user_router
from app.workflows.booking.router import router as booking_router
from app.workflows.refund.router import router as refund_router
from app.workflows.search.router import router as search_router


configure_logging()
logger = get_logger(__name__)
LOGIN_PATH = "/api/auth/login"
REGISTER_PATH = "/api/auth/register"
LOGIN_REQUIRED_FIELDS = (
    ("phone", "手机号"),
    ("password", "密码"),
)
REGISTER_REQUIRED_FIELDS = (
    ("name", "姓名"),
    ("password", "密码"),
    ("phone", "手机号"),
)
PASSWORD_TOO_SHORT_MESSAGE = "请输入至少六位的密码"
DEFAULT_VALIDATION_MESSAGE = "请求参数校验失败"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title="FudanAir API",
    lifespan=lifespan,
)


def _cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in settings.cors_origins_raw.split(",")
        if origin.strip()
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(city_router, prefix="/api")
app.include_router(airport_router, prefix="/api")
app.include_router(airline_router, prefix="/api")
app.include_router(aircraft_type_router, prefix="/api")
app.include_router(flight_router, prefix="/api")
app.include_router(flight_instance_router, prefix="/api")
app.include_router(booking_router, prefix="/api/booking")
app.include_router(user_router, prefix="/api")
app.include_router(passenger_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(admin_order_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(refund_router, prefix="/api/refund")
app.include_router(search_router, prefix="/api/search")


@app.exception_handler(AppException)
async def app_exception_handler(
    _request: Request,
    exc: AppException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": _validation_message(request, exc),
        },
    )


def _validation_message(request: Request, exc: RequestValidationError) -> str:
    if request.url.path == LOGIN_PATH:
        return _login_validation_message(exc.body)
    if request.url.path == REGISTER_PATH:
        return _register_validation_message(exc.body)
    return DEFAULT_VALIDATION_MESSAGE


def _login_validation_message(body: object) -> str:
    if not isinstance(body, dict):
        return _missing_fields_message(LOGIN_REQUIRED_FIELDS)

    missing_labels = _missing_field_labels(body, LOGIN_REQUIRED_FIELDS)
    if missing_labels:
        return _missing_fields_message(missing_labels)

    phone = body.get("phone")
    if not isinstance(phone, str) or not PHONE_PATTERN.fullmatch(phone.strip()):
        return "手机号格式错误"

    return DEFAULT_VALIDATION_MESSAGE


def _register_validation_message(body: object) -> str:
    if not isinstance(body, dict):
        return _missing_fields_message(REGISTER_REQUIRED_FIELDS)

    missing_labels = _missing_field_labels(body, REGISTER_REQUIRED_FIELDS)
    if len(missing_labels) >= 2:
        return _missing_fields_message(missing_labels)
    if missing_labels == ["姓名"]:
        return "请输入姓名"
    if missing_labels == ["手机号"]:
        return "请输入手机号"
    if missing_labels == ["密码"]:
        return PASSWORD_TOO_SHORT_MESSAGE

    password = body.get("password")
    if isinstance(password, str) and len(password.strip()) < REGISTER_PASSWORD_MIN_LENGTH:
        return PASSWORD_TOO_SHORT_MESSAGE
    return DEFAULT_VALIDATION_MESSAGE


def _missing_field_labels(
    body: dict[str, object],
    fields: tuple[tuple[str, str], ...],
) -> list[str]:
    return [
        label
        for field, label in fields
        if _is_blank(body.get(field))
    ]


def _missing_fields_message(fields: tuple[tuple[str, str], ...] | list[str]) -> str:
    labels = [label for _, label in fields] if isinstance(fields, tuple) else fields
    return f"请输入{','.join(labels)}"


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "未处理异常 %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "系统繁忙,请稍后重试"},
    )
