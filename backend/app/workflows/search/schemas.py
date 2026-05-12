from __future__ import annotations

from datetime import date, time, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CabinClass = Literal["经济舱", "头等舱"]
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
    cabin_class: CabinClass | None = None
    departure_time_range: tuple[time, time] | None = None
    include_stopover: bool = True

    model_config = {"str_strip_whitespace": True}

    @field_validator("airline_code")
    @classmethod
    def normalize_airline_code(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @model_validator(mode="after")
    def validate_time_range(self) -> SearchFilters:
        if self.departure_time_range is None:
            return self
        start, end = self.departure_time_range
        if start > end:
            raise ValueError("起飞时间段结束时间不能早于开始时间")
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
    min_price: float
    min_ticket_price: float
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
    min_price: float
    min_ticket_price: float
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
