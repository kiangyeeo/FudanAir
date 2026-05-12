from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


DEAL_STATUSES = ("已支付", "已完成", "部分退款", "已完成退款")


class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(self) -> dict[str, Any]:
        metrics = self._metrics()
        metrics["top_routes"] = self._top_routes()
        return metrics

    def _metrics(self) -> dict[str, int | float]:
        statement = text(
            """
            SELECT
                (SELECT COUNT(*) FROM aptorder) AS total_orders,
                (
                    SELECT COUNT(*)
                    FROM aptorder
                    WHERE created_at >= CURDATE()
                      AND created_at < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
                ) AS today_orders,
                (SELECT COUNT(*) FROM user) AS total_users,
                (
                    SELECT COUNT(DISTINCT user_id)
                    FROM aptorder
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ) AS active_users_30d,
                (
                    SELECT COALESCE(SUM(total_amount), 0)
                    FROM aptorder
                    WHERE created_at >= CURDATE()
                      AND created_at < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
                      AND status IN :deal_statuses
                ) AS today_revenue
            """
        ).bindparams(bindparam("deal_statuses", expanding=True))
        row = self.db.execute(statement, {"deal_statuses": DEAL_STATUSES}).mappings().one()
        return {
            "total_orders": int(row["total_orders"] or 0),
            "today_orders": int(row["today_orders"] or 0),
            "total_users": int(row["total_users"] or 0),
            "active_users_30d": int(row["active_users_30d"] or 0),
            "today_revenue": _to_float(row["today_revenue"]),
        }

    def _top_routes(self) -> list[dict[str, int | str]]:
        statement = text(
            """
            SELECT
                f.dep_airport_code,
                f.arr_airport_code,
                COUNT(DISTINCT o.order_no) AS order_count
            FROM aptorder o
            JOIN ticket t ON o.order_no = t.order_no
            JOIN flight_instance fi ON t.instance_id = fi.instance_id
            JOIN flight f ON fi.flight_no = f.flight_no
            WHERE o.created_at >= CURDATE()
              AND o.created_at < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
              AND o.status IN :deal_statuses
            GROUP BY f.dep_airport_code, f.arr_airport_code
            ORDER BY order_count DESC, f.dep_airport_code, f.arr_airport_code
            LIMIT 5
            """
        ).bindparams(bindparam("deal_statuses", expanding=True))
        rows = self.db.execute(statement, {"deal_statuses": DEAL_STATUSES}).mappings().all()
        return [
            {
                "dep_airport_code": row["dep_airport_code"],
                "arr_airport_code": row["arr_airport_code"],
                "order_count": int(row["order_count"] or 0),
            }
            for row in rows
        ]


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
