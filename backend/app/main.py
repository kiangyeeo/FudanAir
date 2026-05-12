from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.domains.airline.router import (
    aircraft_type_router,
    airline_router,
)
from app.domains.city.router import airport_router, city_router
from app.domains.flight.router import flight_instance_router, flight_router
from app.domains.order.router import admin_order_router, order_router
from app.workflows.booking.router import router as booking_router
from app.workflows.refund.router import router as refund_router
from app.workflows.search.router import router as search_router


configure_logging()
logger = get_logger(__name__)


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
app.include_router(order_router, prefix="/api")
app.include_router(admin_order_router, prefix="/api")
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
    _request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": "请求参数校验失败"},
    )


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
