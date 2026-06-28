from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domains.order.models import AptOrder


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, order_no: str) -> AptOrder | None:
        return self.db.get(AptOrder, order_no)

    def lock_for_update(self, order_no: str) -> AptOrder | None:
        stmt = select(AptOrder).where(AptOrder.order_no == order_no).with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        order_no: str,
        user_id: int,
        total_amount: Decimal,
        status: str,
        created_at: datetime,
    ) -> AptOrder:
        order = AptOrder(
            order_no=order_no,
            user_id=user_id,
            total_amount=total_amount,
            status=status,
            created_at=created_at,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def update_status(self, order: AptOrder, status: str) -> AptOrder:
        order.status = status
        self.db.flush()
        return order

    def list_by_user(
        self,
        user_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["user_id = :user_id"]
        params: dict[str, Any] = {"user_id": user_id}
        if status:
            where.append("status = :status")
            params["status"] = status
        return self._list_summary(where, params, page, page_size)

    def list_all_for_admin(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        user_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        where: list[str] = []
        params: dict[str, Any] = {}
        if status:
            where.append("status = :status")
            params["status"] = status
        if user_id is not None:
            where.append("user_id = :user_id")
            params["user_id"] = user_id
        if date_from is not None:
            where.append("created_at >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            where.append("created_at < :date_to_next")
            params["date_to_next"] = date_to + timedelta(days=1)
        return self._list_summary(where, params, page, page_size)

    def detail_rows(self, order_no: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT
                    o.order_no,
                    o.user_id,
                    o.total_amount,
                    o.status AS order_status,
                    o.created_at,
                    t.ticket_no,
                    t.passenger_id,
                    p.real_name,
                    p.birth_date,
                    t.instance_id,
                    fi.flight_no,
                    fi.flight_date,
                    fi.scheduled_departure,
                    fi.scheduled_arrival,
                    f.dep_airport_code,
                    f.arr_airport_code,
                    fi.adjusted_at,
                    fi.scheduled_departure_adjusted_at,
                    fi.scheduled_arrival_adjusted_at,
                    fi.dep_airport_adjusted_at,
                    fi.arr_airport_adjusted_at,
                    t.fuel_infra_fee,
                    t.cabin_class,
                    t.fare_type,
                    t.actual_price,
                    t.status AS ticket_status
                FROM aptorder o
                LEFT JOIN ticket t ON o.order_no = t.order_no
                LEFT JOIN passenger p ON t.passenger_id = p.id_no
                LEFT JOIN flight_instance fi ON t.instance_id = fi.instance_id
                LEFT JOIN flight f ON fi.flight_no = f.flight_no
                WHERE o.order_no = :order_no
                ORDER BY t.ticket_no
                """
            ),
            {"order_no": order_no},
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_expired_pending_order_nos(self, expire_before: datetime) -> list[str]:
        rows = (
            self.db.query(AptOrder.order_no)
            .filter(
                AptOrder.status == "待支付",
                AptOrder.created_at < expire_before,
            )
            .order_by(AptOrder.created_at)
            .all()
        )
        return [str(row.order_no) for row in rows]

    def _list_summary(
        self,
        where: list[str],
        params: dict[str, Any],
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        total = self.db.execute(
            text(f"SELECT COUNT(*) FROM v_order_summary {where_sql}"),
            params,
        ).scalar_one()
        rows = self.db.execute(
            text(
                f"""
                SELECT
                    order_no,
                    user_id,
                    user_name,
                    total_amount,
                    status,
                    created_at,
                    ticket_count,
                    active_count,
                    refunded_count
                FROM v_order_summary
                {where_sql}
                ORDER BY created_at DESC, order_no DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                **params,
                "limit": page_size,
                "offset": (page - 1) * page_size,
            },
        ).mappings().all()
        return [_summary_row(row) for row in rows], int(total)


def _summary_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in ("ticket_count", "active_count", "refunded_count"):
        data[key] = int(data.get(key) or 0)
    return data
