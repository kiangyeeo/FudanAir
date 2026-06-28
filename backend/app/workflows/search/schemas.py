from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CabinClass = Literal["经济舱", "头等舱"]
FareType = Literal["标准", "特价"]
SortField = Literal["price", "duration", "departure"]
SortOrder = Literal["asc", "desc"]


def normalize_db_time(value: Any) -> Any:
    if not isinstance(value, timedelta):
        return value
    total_seconds = int(value.total_seconds()) % (24 * 60 * 60)
    hour, remainder = divmod(total_seconds, 60 * 60)
    minute, second = divmod(remainder, 60)
    return time(hour=hour, minute=minute, second=second, microsecond=value.microseconds)


class SearchFilters(BaseModel):
    airline_code: str | None = Field(default=None, min_length=2, max_length=2)
    airline_codes: list[str] | None = None
    cabin_class: CabinClass | None = None
    departure_time_range: tuple[time, time] | None = None
    price_min: Decimal | None = Field(default=None, ge=0)
    price_max: Decimal | None = Field(default=None, ge=0)
    include_stopover: bool = True

    model_config = {"str_strip_whitespace": True}

    @field_validator("airline_code")
    @classmethod
    def normalize_airline_code(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @field_validator("airline_codes", mode="before")
    @classmethod
    def normalize_airline_codes(cls, value: Any) -> list[str] | None:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            raw_codes = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_codes = value
        else:
            raise ValueError("航司筛选必须是代码列表")

        codes: list[str] = []
        seen: set[str] = set()
        for raw_code in raw_codes:
            code = str(raw_code or "").strip().upper()
            if not code:
                continue
            if len(code) != 2:
                raise ValueError("航司代码必须为2位")
            if code not in seen:
                seen.add(code)
                codes.append(code)
        return codes or None

    @model_validator(mode="after")
    def validate_filters(self) -> SearchFilters:
        codes = list(self.airline_codes or [])
        if self.airline_code and self.airline_code not in codes:
            codes.insert(0, self.airline_code)
        self.airline_codes = codes or None
        self.airline_code = codes[0] if len(codes) == 1 else None

        if self.departure_time_range is not None:
            start, end = self.departure_time_range
            if start > end:
                raise ValueError("起飞时间段结束时间不能早于开始时间")
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("价格区间上限不能小于下限")
        return self


class SearchSort(BaseModel):
    field: SortField = "price"
    order: SortOrder = "asc"


class FlightSearchRequest(BaseModel):
    dep_city: str = Field(..., min_length=1, max_length=32)
    arr_city: str = Field(..., min_length=1, max_length=32)
    flight_date: date
    filters: SearchFilters = Field(default_factory=SearchFilters)
    sort: SearchSort = Field(default_factory=SearchSort)

    model_config = {"str_strip_whitespace": True}


class DirectFlightCandidate(BaseModel):
    type: Literal["direct"] = "direct"
    instance_id: str
    flight_no: str
    dep_airport_code: str
    arr_airport_code: str
    scheduled_departure: time
    scheduled_arrival: time
    airline_code: str
    airline_name: str
    aircraft_model: str
    min_price: float
    min_ticket_price: float
    min_cabin_class: CabinClass
    min_fare_type: FareType
    fuel_infra_fee: float
    economy_left: int
    first_left: int

    @field_validator("scheduled_departure", "scheduled_arrival", mode="before")
    @classmethod
    def normalize_time_fields(cls, value: Any) -> Any:
        return normalize_db_time(value)


class TransitCandidate(BaseModel):
    type: Literal["transit"] = "transit"
    leg1: DirectFlightCandidate
    leg2: DirectFlightCandidate
    transit_airport: str
    transit_minutes: int
    total_duration_minutes: int
    total_min_price: float
    total_ticket_price: float
    total_fuel_infra_fee: float


class NearbyFlightCandidate(BaseModel):
    type: Literal["nearby"] = "nearby"
    replacement: Literal["departure", "arrival"]
    replaced_airport: str
    actual_dep_city: str | None = None
    actual_arr_city: str | None = None
    instance_id: str
    flight_no: str
    dep_airport_code: str
    arr_airport_code: str
    scheduled_departure: time
    scheduled_arrival: time
    airline_code: str
    airline_name: str
    aircraft_model: str
    min_price: float
    min_ticket_price: float
    min_cabin_class: CabinClass
    min_fare_type: FareType
    fuel_infra_fee: float
    economy_left: int
    first_left: int

    @field_validator("scheduled_departure", "scheduled_arrival", mode="before")
    @classmethod
    def normalize_time_fields(cls, value: Any) -> Any:
        return normalize_db_time(value)


class FlightSearchResponse(BaseModel):
    direct: list[DirectFlightCandidate]
    transit: list[TransitCandidate]
    nearby: list[NearbyFlightCandidate]
