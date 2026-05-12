from __future__ import annotations

from pydantic import BaseModel


class DashboardRoute(BaseModel):
    dep_airport_code: str
    arr_airport_code: str
    order_count: int


class DashboardResponse(BaseModel):
    total_orders: int
    today_orders: int
    total_users: int
    active_users_30d: int
    today_revenue: float
    top_routes: list[DashboardRoute]
