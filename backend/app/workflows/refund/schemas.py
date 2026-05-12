from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CabinClass = Literal["经济舱", "头等舱"]
FareType = Literal["标准", "特价"]
RefundOperation = Literal["refund", "change"]


class RefundTicketRequest(BaseModel):
    ticket_no: str = Field(..., min_length=1, max_length=32)

    model_config = {"str_strip_whitespace": True}


class ChangeTicketRequest(RefundTicketRequest):
    new_instance_id: str = Field(..., min_length=1, max_length=32)
    new_cabin_class: CabinClass
    new_fare_type: FareType


class RefundQuoteResponse(BaseModel):
    ticket_no: str
    op_type: RefundOperation
    actual_price: float | None = None
    old_actual_price: float | None = None
    new_actual_price: float | None = None
    fee_rate: float
    fee: float
    refund_amount: float | None = None
    price_diff: float | None = None
    amount_user_pays: float | None = None
    tier: str


class RefundTicketResponse(BaseModel):
    refund_id: int
    ticket_no: str
    fee: float
    refund_amount: float
    ticket_status: Literal["已退"]
    order_status: Literal["部分退款", "已完成退款"]


class ChangeTicketResponse(BaseModel):
    refund_id: int
    old_ticket_no: str
    new_ticket_no: str
    fee: float
    price_diff: float
    amount_user_pays: float
    old_ticket_status: Literal["已改签作废"]
    new_ticket_status: Literal["有效"]
