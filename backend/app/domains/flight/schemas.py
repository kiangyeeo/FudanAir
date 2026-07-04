from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CabinClass = Literal["经济舱", "头等舱"]
FareType = Literal["标准", "特价"]
InstanceStatus = Literal["计划", "可订", "已起飞", "已到达", "已取消"]


def normalize_db_time(value: Any) -> Any:
    if not isinstance(value, timedelta):
        return value
    total_seconds = int(value.total_seconds()) % (24 * 60 * 60)
    hour, remainder = divmod(total_seconds, 60 * 60)
    minute, second = divmod(remainder, 60)
    return time(hour=hour, minute=minute, second=second, microsecond=value.microseconds)


class FlightBase(BaseModel):
    scheduled_departure: time
    scheduled_arrival: time
    fuel_infra_fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    base_price: Decimal = Field(..., ge=Decimal("0"))
    dep_airport_code: str = Field(..., min_length=3, max_length=3)
    dep_terminal: str | None = Field(default=None, max_length=8)
    arr_airport_code: str = Field(..., min_length=3, max_length=3)
    arr_terminal: str | None = Field(default=None, max_length=8)
    airline_code: str = Field(..., min_length=2, max_length=2)
    aircraft_model: str = Field(..., min_length=1, max_length=32)
    weekdays: list[int] = Field(..., min_length=1)
    stopovers: list[str] = Field(default_factory=list)

    model_config = {"str_strip_whitespace": True}

    @model_validator(mode="after")
    def validate_weekdays(self) -> FlightBase:
        if any(day < 1 or day > 7 for day in self.weekdays):
            raise ValueError("Operating weekdays must be between 1 and 7.")
        if self.scheduled_departure > self.scheduled_arrival:
            raise ValueError("Departure time cannot be later than arrival time.")
        return self


class FlightCreate(FlightBase):
    flight_no: str = Field(..., min_length=1, max_length=8)


class FlightUpdate(FlightBase):
    pass


class FlightListResponse(BaseModel):
    flight_no: str
    scheduled_departure: time
    scheduled_arrival: time
    fuel_infra_fee: float
    base_price: float
    dep_airport_code: str
    dep_terminal: str | None = None
    arr_airport_code: str
    arr_terminal: str | None = None
    airline_code: str
    aircraft_model: str

    model_config = {"from_attributes": True}

    @field_validator("scheduled_departure", "scheduled_arrival", mode="before")
    @classmethod
    def normalize_time_fields(cls, value: Any) -> Any:
        return normalize_db_time(value)


class FlightDetailResponse(FlightListResponse):
    airline_name: str | None = None
    weekdays: list[int]
    stopovers: list[str]


class FlightPageResponse(BaseModel):
    items: list[FlightListResponse]
    total: int
    page: int
    page_size: int


class FlightInstanceCreate(BaseModel):
    flight_no: str = Field(..., min_length=1, max_length=8)
    flight_date: date

    model_config = {"str_strip_whitespace": True}


class FlightInstanceBatchCreate(BaseModel):
    flight_no: str = Field(..., min_length=1, max_length=8)
    start_date: date
    end_date: date

    model_config = {"str_strip_whitespace": True}

    @model_validator(mode="after")
    def validate_date_range(self) -> FlightInstanceBatchCreate:
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date.")
        return self


class FlightInstanceUpdate(BaseModel):
    scheduled_departure: time | None = None
    scheduled_arrival: time | None = None
    fuel_infra_fee: Decimal | None = Field(default=None, ge=Decimal("0"))

    model_config = {"str_strip_whitespace": True}

    @model_validator(mode="after")
    def validate_time_order(self) -> FlightInstanceUpdate:
        if (
            self.scheduled_departure is not None
            and self.scheduled_arrival is not None
            and self.scheduled_departure > self.scheduled_arrival
        ):
            raise ValueError("Departure time cannot be later than arrival time.")
        return self

class FlightInstanceStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=8)

    model_config = {"str_strip_whitespace": True}


class FlightInstanceListResponse(BaseModel):
    instance_id: str
    flight_no: str
    flight_date: date
    scheduled_departure: time
    scheduled_arrival: time
    fuel_infra_fee: float
    adjusted_at: datetime | None = None
    scheduled_departure_adjusted_at: datetime | None = None
    scheduled_arrival_adjusted_at: datetime | None = None
    dep_airport_adjusted_at: datetime | None = None
    arr_airport_adjusted_at: datetime | None = None
    economy_left: int
    first_left: int
    status: str

    model_config = {"from_attributes": True}

class CabinPriceResponse(BaseModel):
    instance_id: str
    cabin_class: CabinClass
    fare_type: FareType
    price: float
    available_seats: int

    model_config = {"from_attributes": True}


class FlightInstanceDetailResponse(FlightInstanceListResponse):
    dep_airport_code: str
    arr_airport_code: str
    airline_code: str
    airline_name: str | None = None
    cabin_prices: list[CabinPriceResponse]

    @field_validator("scheduled_departure", "scheduled_arrival", mode="before")
    @classmethod
    def normalize_time_fields(cls, value: Any) -> Any:
        return normalize_db_time(value)

class FlightInstancePageResponse(BaseModel):
    items: list[FlightInstanceListResponse]
    total: int
    page: int
    page_size: int


class CabinPriceSetItem(BaseModel):
    cabin_class: CabinClass
    fare_type: FareType
    price: Decimal = Field(..., ge=Decimal("0"))
    available_seats: int = Field(..., ge=0)


class CabinPriceReplace(BaseModel):
    cabin_prices: list[CabinPriceSetItem] = Field(..., min_length=1)
