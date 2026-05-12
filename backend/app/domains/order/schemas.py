from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Literal

from pydantic import BaseModel, field_validator


OrderStatus = Literal["待支付", "已支付", "已取消", "已完成", "部分退款", "已完成退款"]


def normalize_db_time(value: Any) -> Any:
    if not isinstance(value, timedelta):
        return value
    total_seconds = int(value.total_seconds()) % (24 * 60 * 60)
    hour, remainder = divmod(total_seconds, 60 * 60)
    minute, second = divmod(remainder, 60)
    return time(hour=hour, minute=minute, second=second, microsecond=value.microseconds)


class OrderListItem(BaseModel):
    order_no: str
    user_id: int
    user_name: str | None = None
    status: OrderStatus
    total_amount: float
    created_at: datetime
    ticket_count: int = 0
    active_count: int = 0
    refunded_count: int = 0


class OrderPageResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    page_size: int


class OrderPassengerBrief(BaseModel):
    id_no: str
    real_name: str


class OrderTicketDetail(BaseModel):
    ticket_no: str
    passenger: OrderPassengerBrief
    instance_id: str
    flight_no: str
    flight_date: date
    scheduled_departure: time
    scheduled_arrival: time | None = None
    dep_airport_code: str
    arr_airport_code: str
    cabin_class: Literal["经济舱", "头等舱"]
    fare_type: Literal["标准", "特价"]
    ticket_price: float | None = None
    fuel_infra_fee: float | None = None
    actual_price: float
    status: Literal["有效", "已退", "已改签作废", "已使用"]

    @field_validator("scheduled_departure", "scheduled_arrival", mode="before")
    @classmethod
    def normalize_time_fields(cls, value: Any) -> Any:
        return normalize_db_time(value)


class OrderDetailResponse(BaseModel):
    order_no: str
    user_id: int
    status: OrderStatus
    total_amount: float
    created_at: datetime
    tickets: list[OrderTicketDetail]
