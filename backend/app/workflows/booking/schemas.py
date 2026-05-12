from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


CabinClass = Literal["经济舱", "头等舱"]
FareType = Literal["标准", "特价"]


class BookingPassenger(BaseModel):
    id_no: str = Field(..., min_length=1, max_length=32)
    real_name: str = Field(..., min_length=1, max_length=64)
    birth_date: date

    model_config = {"str_strip_whitespace": True}


class BookingRequest(BaseModel):
    instance_id: str = Field(..., min_length=1, max_length=32)
    cabin_class: CabinClass
    fare_type: FareType
    passengers: list[BookingPassenger] = Field(..., min_length=1)

    model_config = {"str_strip_whitespace": True}


class BookingTicketResponse(BaseModel):
    ticket_no: str
    passenger_id: str
    actual_price: float


class BookingAmountBreakdown(BaseModel):
    ticket_price_per_seat: float
    fuel_infra_fee_per_seat: float
    seat_count: int


class BookingResponse(BaseModel):
    order_no: str
    status: Literal["待支付"]
    total_amount: float
    amount_breakdown: BookingAmountBreakdown
    created_at: datetime
    expires_at: datetime
    tickets: list[BookingTicketResponse]


class PayResponse(BaseModel):
    order_no: str
    status: Literal["已支付"]
    paid_at: datetime
