from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user_id
from app.deps import get_db
from app.domains.order.schemas import OrderDetailResponse, OrderPageResponse
from app.domains.order.service import OrderService


order_router = APIRouter(prefix="/orders", tags=["order"])
admin_order_router = APIRouter(prefix="/admin/orders", tags=["admin-order"])
router = order_router


@order_router.get("", response_model=OrderPageResponse)
def list_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return OrderService(db).list_by_user(user_id, page, page_size, status)


@order_router.get("/{order_no}", response_model=OrderDetailResponse)
def get_order_detail(
    order_no: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return OrderService(db).get_detail(order_no, user_id)


@admin_order_router.get(
    "",
    response_model=OrderPageResponse,
    dependencies=[Depends(get_current_admin)],
)
def list_all_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return OrderService(db).list_all_for_admin(
        page,
        page_size,
        status,
        user_id,
        date_from,
        date_to,
    )
