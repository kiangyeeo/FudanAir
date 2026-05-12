from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import AppException, ResourceNotFoundError
from app.core.id_generator import gen_order_no
from app.domains.order.models import AptOrder
from app.domains.order.repository import OrderRepository


ALLOWED_ORDER_STATUSES = {"待支付", "已支付", "已取消", "已完成", "部分退款", "已完成退款"}


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrderRepository(db)

    def create(self, user_id: int, total_amount: Decimal) -> AptOrder:
        try:
            with transaction(self.db):
                return self.repo.create(
                    order_no=gen_order_no(),
                    user_id=user_id,
                    total_amount=total_amount,
                    status="待支付",
                    created_at=datetime.now(),
                )
        except IntegrityError as exc:
            raise AppException("订单创建失败") from exc

    def lock_for_update(self, order_no: str) -> AptOrder:
        order = self.repo.lock_for_update(order_no)
        if not order:
            raise ResourceNotFoundError(f"订单 {order_no} 不存在")
        return order

    def update_status(self, order: AptOrder, status: str) -> AptOrder:
        normalized_status = _order_status(status)
        try:
            with transaction(self.db):
                return self.repo.update_status(order, normalized_status)
        except IntegrityError as exc:
            raise AppException(f"订单 {order.order_no} 状态更新失败") from exc

    def list_by_user(
        self,
        user_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> dict[str, object]:
        items, total = self.repo.list_by_user(
            user_id,
            page,
            page_size,
            _optional_order_status(status),
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_detail(self, order_no: str, user_id: int | None = None) -> dict[str, Any]:
        rows = self.repo.detail_rows(order_no)
        if not rows:
            raise ResourceNotFoundError(f"订单 {order_no} 不存在")
        order_user_id = int(rows[0]["user_id"])
        if user_id is not None and order_user_id != user_id:
            raise ResourceNotFoundError(f"订单 {order_no} 不存在")
        tickets = [_ticket_detail(row) for row in rows if row.get("ticket_no")]
        return {
            "order_no": rows[0]["order_no"],
            "user_id": order_user_id,
            "status": rows[0]["order_status"],
            "total_amount": rows[0]["total_amount"],
            "created_at": rows[0]["created_at"],
            "tickets": tickets,
        }

    def list_all_for_admin(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        user_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, object]:
        items, total = self.repo.list_all_for_admin(
            page,
            page_size,
            _optional_order_status(status),
            user_id,
            date_from,
            date_to,
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}


def _ticket_detail(row: dict[str, Any]) -> dict[str, Any]:
    actual_price = row["actual_price"]
    fuel_fee = row["fuel_infra_fee"]
    ticket_price = actual_price - fuel_fee if actual_price is not None and fuel_fee is not None else None
    return {
        "ticket_no": row["ticket_no"],
        "passenger": {
            "id_no": row["passenger_id"],
            "real_name": row["real_name"],
        },
        "instance_id": row["instance_id"],
        "flight_no": row["flight_no"],
        "flight_date": row["flight_date"],
        "scheduled_departure": row["scheduled_departure"],
        "scheduled_arrival": row["scheduled_arrival"],
        "dep_airport_code": row["dep_airport_code"],
        "arr_airport_code": row["arr_airport_code"],
        "cabin_class": row["cabin_class"],
        "fare_type": row["fare_type"],
        "ticket_price": ticket_price,
        "fuel_infra_fee": fuel_fee,
        "actual_price": actual_price,
        "status": row["ticket_status"],
    }


def _order_status(value: str) -> str:
    normalized = value.strip()
    if normalized not in ALLOWED_ORDER_STATUSES:
        raise AppException("订单状态不合法")
    return normalized


def _optional_order_status(value: str | None) -> str | None:
    return _order_status(value) if value else None
