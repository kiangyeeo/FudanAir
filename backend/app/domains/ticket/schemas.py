from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


TicketStatus = Literal["有效", "已退", "已改签作废", "已使用"]
RefundOpType = Literal["退票", "改签"]


class TicketResponse(BaseModel):
    ticket_no: str
    order_no: str
    passenger_id: str
    instance_id: str
    cabin_class: Literal["经济舱", "头等舱"]
    fare_type: Literal["标准", "特价"]
    actual_price: float
    status: TicketStatus

    model_config = {"from_attributes": True}


class RefundChangeRecordResponse(BaseModel):
    refund_id: int
    ticket_no: str
    op_type: RefundOpType
    fee: float
    new_ticket_no: str | None = None
    price_diff: float
    op_time: datetime


class RefundChangePageResponse(BaseModel):
    items: list[RefundChangeRecordResponse]
    total: int
    page: int
    page_size: int
