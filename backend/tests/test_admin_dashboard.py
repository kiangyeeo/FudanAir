from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.auth.dependencies import get_current_admin
from app.core.exceptions import AppException
from app.deps import get_db
from app.domains.admin.repository import DEAL_STATUSES, AdminRepository
from app.domains.admin.router import router


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def mappings(self) -> FakeResult:
        return self

    def one(self) -> dict[str, Any]:
        return self.rows[0]

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class FakeSession:
    def __init__(self, rows_by_call: list[list[dict[str, Any]]]):
        self.rows_by_call = rows_by_call
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any]) -> FakeResult:
        self.calls.append((str(statement), params))
        return FakeResult(self.rows_by_call.pop(0))


def test_dashboard_repository_uses_aggregate_metrics_sql() -> None:
    db = FakeSession(
        [
            [
                {
                    "total_orders": 12,
                    "today_orders": 3,
                    "total_users": 5,
                    "active_users_30d": 4,
                    "today_revenue": Decimal("2600.50"),
                }
            ],
            [],
        ]
    )

    data = AdminRepository(db).get_dashboard()

    metrics_sql, metrics_params = db.calls[0]
    assert "SELECT COUNT(*) FROM aptorder" in metrics_sql
    assert "SELECT COUNT(*) FROM user" in metrics_sql
    assert "COUNT(DISTINCT user_id)" in metrics_sql
    assert "COALESCE(SUM(total_amount), 0)" in metrics_sql
    assert "created_at >= CURDATE()" in metrics_sql
    assert "created_at < DATE_ADD(CURDATE(), INTERVAL 1 DAY)" in metrics_sql
    assert "DATE_SUB(NOW(), INTERVAL 30 DAY)" in metrics_sql
    assert "status IN" in metrics_sql
    assert metrics_params["deal_statuses"] == DEAL_STATUSES
    assert data["today_revenue"] == 2600.5


def test_dashboard_repository_groups_top_routes_by_airport_code() -> None:
    db = FakeSession(
        [
            [
                {
                    "total_orders": 0,
                    "today_orders": 0,
                    "total_users": 0,
                    "active_users_30d": 0,
                    "today_revenue": Decimal("0.00"),
                }
            ],
            [
                {
                    "dep_airport_code": "SHA",
                    "arr_airport_code": "PEK",
                    "order_count": 2,
                }
            ],
        ]
    )

    data = AdminRepository(db).get_dashboard()

    route_sql, route_params = db.calls[1]
    assert "COUNT(DISTINCT o.order_no) AS order_count" in route_sql
    assert "JOIN ticket t ON o.order_no = t.order_no" in route_sql
    assert "JOIN flight_instance fi ON t.instance_id = fi.instance_id" in route_sql
    assert "JOIN flight f ON fi.flight_no = f.flight_no" in route_sql
    assert "GROUP BY f.dep_airport_code, f.arr_airport_code" in route_sql
    assert "ORDER BY order_count DESC" in route_sql
    assert "LIMIT 5" in route_sql
    assert route_params["deal_statuses"] == DEAL_STATUSES
    assert data["top_routes"] == [
        {"dep_airport_code": "SHA", "arr_airport_code": "PEK", "order_count": 2}
    ]


def test_dashboard_endpoint_requires_admin_identity() -> None:
    app = _make_app(
        FakeSession(
            [
                [
                    {
                        "total_orders": 1,
                        "today_orders": 1,
                        "total_users": 1,
                        "active_users_30d": 1,
                        "today_revenue": Decimal("800.00"),
                    }
                ],
                [],
            ]
        )
    )
    client = TestClient(app)

    response = client.get("/api/admin/dashboard")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"

    app.dependency_overrides[get_current_admin] = lambda: object()
    response = client.get("/api/admin/dashboard")

    assert response.status_code == 200
    assert response.json()["total_orders"] == 1


def _make_app(db: FakeSession) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db

    @app.exception_handler(AppException)
    async def app_exception_handler(
        _request: Request,
        exc: AppException,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    return app
