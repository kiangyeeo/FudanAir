from __future__ import annotations

from dataclasses import dataclass
from datetime import time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.core.constants import (
    DEFAULT_ECONOMY_BASE_PRICE,
    DEFAULT_ECONOMY_MINUTE_RATE,
    DEFAULT_ECONOMY_SPECIAL_DISCOUNT,
    DEFAULT_FIRST_CLASS_MULTIPLIER,
    DEFAULT_PRICE_STEP,
    ECONOMY_STANDARD_RATIO,
)


_MINUTES_PER_DAY = 24 * 60
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class CabinPriceSpec:
    cabin_class: str
    fare_type: str
    price: Decimal
    available_seats: int


def default_cabin_price_specs(
    economy_seats: int,
    first_seats: int,
    departure_time: Any,
    arrival_time: Any,
) -> list[CabinPriceSpec]:
    economy_standard, economy_special = split_economy_seats(economy_seats)
    standard_price, special_price, first_price = default_price_set(
        departure_time,
        arrival_time,
    )
    specs = [
        CabinPriceSpec("经济舱", "标准", standard_price, economy_standard),
        CabinPriceSpec("经济舱", "特价", special_price, economy_special),
    ]
    if first_seats > 0:
        specs.append(CabinPriceSpec("头等舱", "标准", first_price, first_seats))
    return specs


def split_economy_seats(total: int) -> tuple[int, int]:
    ratio = Decimal(str(ECONOMY_STANDARD_RATIO))
    standard = int((Decimal(total) * ratio).to_integral_value(rounding=ROUND_HALF_UP))
    standard = min(max(standard, 0), total)
    return standard, total - standard


def default_price_set(departure_time: Any, arrival_time: Any) -> tuple[Decimal, Decimal, Decimal]:
    duration = Decimal(flight_duration_minutes(departure_time, arrival_time))
    economy_price = _round_price(
        Decimal(DEFAULT_ECONOMY_BASE_PRICE)
        + Decimal(DEFAULT_ECONOMY_MINUTE_RATE) * duration
    )
    special_price = _round_price(economy_price * Decimal(DEFAULT_ECONOMY_SPECIAL_DISCOUNT))
    first_price = _round_price(economy_price * Decimal(DEFAULT_FIRST_CLASS_MULTIPLIER))
    return economy_price, special_price, first_price


def flight_duration_minutes(departure_time: Any, arrival_time: Any) -> int:
    dep_minutes = _time_to_minutes(departure_time)
    arr_minutes = _time_to_minutes(arrival_time)
    if arr_minutes <= dep_minutes:
        arr_minutes += _MINUTES_PER_DAY
    return arr_minutes - dep_minutes


def _time_to_minutes(value: Any) -> int:
    if isinstance(value, timedelta):
        return int(value.total_seconds() // 60)
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, str):
        hour, minute, *_ = value.split(":")
        return int(hour) * 60 + int(minute)
    raise TypeError(f"无法解析 TIME 字段: {value!r}")


def _round_price(value: Decimal) -> Decimal:
    price_step = Decimal(DEFAULT_PRICE_STEP)
    rounded = (value / price_step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (rounded * price_step).quantize(_CENT)
